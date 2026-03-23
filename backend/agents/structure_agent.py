# backend/agents/structure_agent.py - AI-powered business structure extraction

import json
import os
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from groq import Groq

from utils.logger import get_logger

# Setup logging
logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Lazy-initialized client (avoid init with None key)
_client = None


def _get_groq_client() -> Groq:
    """Get or create Groq client with lazy initialization"""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Please configure it in your .env file."
            )
        _client = Groq(api_key=api_key)
    return _client

# Available models (tried in order of preference)
MODELS = [
    "llama-3.3-70b-versatile",  # Latest high limit
    "llama-3.1-8b-instant",      # Fallback
    "mixtral-8x7b-32768",        # Alternative
]


# ─── JSON Extraction ───────────────────────────────────────────────────────────────

def extract_json(text: str) -> Dict[str, Any]:
    """
    Extract JSON from text response.

    Args:
        text: Text containing JSON

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If no valid JSON found
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("No JSON found in response")

    return json.loads(match.group())


# ─── Hallucination Filter ───────────────────────────────────────────────────────────

def validate_items(items: List[Dict], research_text: str) -> List[Dict]:
    """
    Validate extracted items against research data to filter hallucinations.

    Args:
        items: List of extracted structure items
        research_text: Original research data to validate against

    Returns:
        List of validated items that exist in research text
    """
    valid = []
    research_lower = research_text.lower()

    for item in items:
        name = item.get("name", "").lower()

        if name and name in research_lower:
            valid.append(item)

    logger.debug(f"Validated {len(items)} items, {len(valid)} passed")
    return valid


# ─── Tree Normalization ───────────────────────────────────────────────────────────

def normalize_tree(tree: Dict[str, Any], max_depth: Optional[int] = None) -> Dict[str, Any]:
    """
    Normalize tree structure - removes empty nodes.

    Args:
        tree: Raw tree structure from AI
        max_depth: Maximum depth to traverse (None = unlimited)

    Returns:
        Cleaned tree structure
    """
    def clean_node(node: Dict[str, Any], depth: int = 0) -> Optional[Dict[str, Any]]:
        if max_depth and depth >= max_depth:
            if node.get("children"):
                return {"name": node["name"], "children": node["children"]}
            return node

        if "name" not in node:
            return None

        cleaned = {"name": node["name"]}
        children = node.get("children", [])

        cleaned_children = []

        for child in children:
            c = clean_node(child, depth + 1)
            if c:
                cleaned_children.append(c)

        if cleaned_children:
            cleaned["children"] = cleaned_children

        return cleaned

    return clean_node(tree)


# ─── Fallback Structure ───────────────────────────────────────────────────────────

def fallback_structure(company: str, research_text: str) -> Dict[str, Any]:
    """
    Generate a basic structure when AI fails.
    Uses keyword extraction from research text.

    Args:
        company: Company name
        research_text: Research data to extract keywords from

    Returns:
        Basic structure dictionary
    """
    logger.warning("Using fallback structure generation")

    keywords = [
        "consulting", "digital", "engineering",
        "products", "services", "cloud", "ai"
    ]

    found = []

    for k in keywords:
        if k in research_text.lower():
            found.append({"name": k.capitalize()})

    return {
        "name": company,
        "children": [
            {
                "name": "Business",
                "children": found
            }
        ]
    }


# ─── Main Structure Extraction ───────────────────────────────────────────────────

def extract_structure(company: str, research_data: List[str]) -> Dict[str, Any]:
    """
    Extract business structure from research data using AI.

    Args:
        company: Company name
        research_data: List of research text from various sources

    Returns:
        Hierarchical business structure as dictionary
    """
    logger.info(f"Extracting structure for: {company}")

    # Limit research data to prevent token limit exceeded errors
    # Take top 5 sources and truncate each to 1500 chars
    research_text = "\n\n".join([t[:1500] for t in research_data[:5]])

    logger.debug(f"Research text length: {len(research_text)} chars")

    prompt = f"""
You are a senior business analyst specializing in corporate structure analysis.

Extract the ACTUAL organizational structure of the company from the given research data.
DO NOT use fixed categories. Discover what the company actually has - it could be divisions,
strategic business units, product lines, subsidiaries, operating segments, etc.

RULES:
- Only use provided data - NEVER invent information not in the data
- If unsure about something, skip it
- Discover REAL categories from the data (e.g., "Digital Services", "Refining", "Jio Platforms", "Retail")
- Use meaningful, specific names - NOT generic ones like "Products" or "Divisions"
- Let the depth be determined by the actual company structure (could be 2-10+ levels)
- Return ONLY JSON

Structure format - discover the actual hierarchy:

{{
  "name": "{company}",
  "children": [
    {{
      "name": "ACTUAL_CATEGORY_NAME_1",
      "children": [
        {{
          "name": "Sub-category or Business Unit",
          "children": [{{"name": "Specific product/service/entity"}}]
        }}
      ]
    }},
    {{
      "name": "ACTUAL_CATEGORY_NAME_2",
      "children": [...]
    }}
  ]
}}

DATA:
{research_text}
"""

    # Try each model in order
    for model in MODELS:
        try:
            logger.info(f"Attempting structure extraction with model: {model}")

            response = _get_groq_client().chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                temperature=0  # Deterministic output
            )

            if not response.choices:
                logger.warning(f"Model {model} returned empty choices")
                continue

            content = response.choices[0].message.content.strip()

            logger.debug(f"AI response (first 500 chars): {content[:500]}")

            data = extract_json(content)

            # Validate extracted items against research data
            for category in data.get("children", []):
                category["children"] = validate_items(
                    category.get("children", []),
                    research_text
                )

            # Remove empty categories
            data["children"] = [
                c for c in data["children"] if c.get("children")
            ]

            # Normalize tree
            data = normalize_tree(data)

            if not data or not data.get("children"):
                raise ValueError("Empty structure after validation")

            logger.info(f"Structure extraction successful using {model}")
            return data

        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            continue

    # All models failed, use fallback
    logger.error(f"All models failed for {company}, using fallback")
    return fallback_structure(company, research_text)