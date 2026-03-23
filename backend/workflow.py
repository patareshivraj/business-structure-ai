# backend/workflow.py - LangGraph workflow orchestration with structured logging

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from agents.research_agent import research_company
from agents.structure_agent import extract_structure
from utils.logger import get_logger

# Setup logging
logger = get_logger(__name__)


# ─── State Definition ───────────────────────────────────────────────────────────────

class State(TypedDict, total=False):
    """State for the LangGraph workflow"""
    company: str
    research_data: List[str]
    tree: Dict[str, Any]


# ─── Workflow Nodes ───────────────────────────────────────────────────────────────

def research_node(state: State) -> Dict[str, Any]:
    """
    Research node - gathers company information from multiple sources.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with research_data
    """
    company = state["company"]
    logger.info(f"Starting research for: {company}")
    
    data = research_company(company)
    
    logger.info(f"Research complete: {len(data)} sources collected")
    return {"research_data": data}


def extract_node(state: State) -> Dict[str, Any]:
    """
    Extract node - uses AI to convert research data into business structure.
    
    Args:
        state: Current workflow state with research_data
        
    Returns:
        Updated state with tree structure
    """
    logger.info("Starting structure extraction")
    
    research_data = state.get("research_data", [])
    
    if not research_data:
        logger.warning("No research data available for structure extraction")
        return {
            "tree": {
                "name": state["company"],
                "children": []
            }
        }
    
    tree = extract_structure(state["company"], research_data)
    
    logger.info("Structure extraction complete")
    return {"tree": tree}


# ─── Build and Compile Graph ─────────────────────────────────────────────────────

builder = StateGraph(State)

# Add nodes
builder.add_node("research", research_node)
builder.add_node("extract", extract_node)

# Set entry point
builder.set_entry_point("research")

# Add edges
builder.add_edge("research", "extract")
builder.add_edge("extract", END)

# Compile the graph
graph = builder.compile()

logger.info("LangGraph workflow compiled successfully")