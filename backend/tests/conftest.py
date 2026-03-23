# backend/tests/conftest.py - Pytest fixtures and configuration

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before each test"""
    from utils.cache import clear_cache
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def sample_company_data():
    """Sample company data for testing"""
    return {
        "company": "TestCompany",
        "research_data": [
            "TestCompany is a technology company.",
            "They offer consulting services.",
            "Products include software and hardware.",
            "Operating in cloud computing sector."
        ]
    }


@pytest.fixture
def sample_tree_structure():
    """Sample business tree structure"""
    return {
        "name": "TestCompany",
        "children": [
            {
                "name": "Products",
                "children": [
                    {"name": "Software"},
                    {"name": "Hardware"}
                ]
            },
            {
                "name": "Services",
                "children": [
                    {"name": "Consulting"},
                    {"name": "Support"}
                ]
            }
        ]
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")
    return monkeypatch
