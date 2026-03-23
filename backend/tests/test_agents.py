# backend/tests/test_agents.py - Agent tests

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResearchAgent:
    """Test research agent functionality"""

    def test_clean_text_basic(self):
        """Test text cleaning function"""
        from agents.research_agent import clean_text

        # Valid text
        valid_text = "A" * 300
        assert len(clean_text(valid_text)) > 0

        # Too short text should return empty
        short_text = "short"
        assert clean_text(short_text) == ""

        # None handling
        assert clean_text(None) == ""

        # Whitespace handling
        assert clean_text("   ") == ""

    def test_clean_text_truncation(self):
        """Test text is truncated to max length"""
        from agents.research_agent import clean_text

        long_text = "A" * 10000
        result = clean_text(long_text)

        assert len(result) <= 5000

    @patch('agents.research_agent.requests.get')
    def test_scrape_page_success(self, mock_get):
        """Test successful page scraping"""
        from agents.research_agent import scrape_page

        # Mock response
        mock_response = MagicMock()
        mock_response.text = '<html><p>Test paragraph content here.</p></html>'
        mock_get.return_value = mock_response

        result = scrape_page("http://test.com")

        # Should return cleaned text
        assert isinstance(result, str)

    @patch('agents.research_agent.requests.get')
    def test_scrape_page_failure(self, mock_get):
        """Test failed page scraping"""
        from agents.research_agent import scrape_page
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        result = scrape_page("http://test.com")

        assert result == ""


class TestStructureAgent:
    """Test structure extraction agent"""

    def test_extract_json_success(self):
        """Test JSON extraction from text"""
        from agents.structure_agent import extract_json

        text = '```json\n{"name": "Company", "children": []}\n```'
        result = extract_json(text)

        assert result["name"] == "Company"

    def test_extract_json_no_json(self):
        """Test JSON extraction with no JSON"""
        from agents.structure_agent import extract_json

        with pytest.raises(Exception) as exc_info:
            extract_json("No JSON here")
        assert "No JSON found" in str(exc_info.value)

    def test_validate_items(self):
        """Test item validation against research text"""
        from agents.structure_agent import validate_items

        items = [
            {"name": "Consulting"},
            {"name": "InvalidItem12345"},
            {"name": "Products"}
        ]
        research_text = "We offer Consulting services and Products"

        result = validate_items(items, research_text)

        assert len(result) == 2
        assert any(item["name"] == "Consulting" for item in result)

    def test_normalize_tree(self):
        """Test tree normalization"""
        from agents.structure_agent import normalize_tree

        deep_tree = {
            "name": "Company",
            "children": [
                {
                    "name": "Level1",
                    "children": [
                        {
                            "name": "Level2",
                            "children": [
                                {"name": "Level3"},
                                {"name": "Level3TooDeep"}
                            ]
                        }
                    ]
                }
            ]
        }

        result = normalize_tree(deep_tree)

        # Should handle depth limits
        assert "name" in result

    def test_fallback_structure(self):
        """Test fallback structure generation"""
        from agents.structure_agent import fallback_structure

        research_text = "We provide consulting digital engineering and cloud services"

        result = fallback_structure("TestCompany", research_text)

        assert result["name"] == "TestCompany"
        assert "children" in result


class TestWorkflow:
    """Test workflow orchestration"""

    def test_research_node(self):
        """Test research node execution"""
        from workflow import research_node, State

        # Mock research_company
        with patch('workflow.research_company') as mock_research:
            mock_research.return_value = ["Research data"]

            state: State = {"company": "Test"}
            result = research_node(state)

            assert "research_data" in result
            assert result["research_data"] == ["Research data"]

    def test_extract_node_no_data(self):
        """Test extract node with no research data"""
        from workflow import extract_node, State

        state: State = {"company": "Test", "research_data": []}

        result = extract_node(state)

        assert "tree" in result
        assert result["tree"]["name"] == "Test"
        assert result["tree"]["children"] == []

    def test_graph_compilation(self):
        """Test graph is compiled correctly"""
        from workflow import graph, builder

        # Verify graph exists and is compiled
        assert graph is not None
        assert hasattr(graph, 'invoke')


class TestCache:
    """Test cache functionality"""

    def test_get_cache(self):
        """Test cache get"""
        from utils.cache import get_cache, set_cache, clear_cache

        clear_cache()

        # Should return None for non-existent key
        result = get_cache("nonexistent")
        assert result is None

        # Set and get
        set_cache("test_key", "test_value")
        result = get_cache("test_key")
        assert result == "test_value"

        clear_cache()

    def test_set_cache(self):
        """Test cache set"""
        from utils.cache import set_cache, get_cache, clear_cache

        clear_cache()

        test_data = {"name": "Test", "children": []}
        set_cache("company", test_data)

        result = get_cache("company")
        assert result == test_data

        clear_cache()

    def test_clear_cache(self):
        """Test cache clear"""
        from utils.cache import set_cache, get_cache, clear_cache

        set_cache("key1", "value1")
        set_cache("key2", "value2")

        clear_cache("key1")

        assert get_cache("key1") is None
        assert get_cache("key2") == "value2"

        clear_cache()

    def test_clear_all_cache(self):
        """Test clearing entire cache"""
        from utils.cache import set_cache, get_cache, clear_cache

        set_cache("key1", "value1")
        set_cache("key2", "value2")

        clear_cache()

        assert get_cache("key1") is None
        assert get_cache("key2") is None


class TestAsyncCache:
    """Test async cache functionality"""

    @pytest.mark.asyncio
    async def test_async_get_cache(self):
        """Test async cache get"""
        from utils.cache import get_cache_async, set_cache_async, clear_cache_async

        await clear_cache_async()

        result = await get_cache_async("nonexistent")
        assert result is None

        await set_cache_async("async_key", "async_value")
        result = await get_cache_async("async_key")
        assert result == "async_value"

        await clear_cache_async()

    @pytest.mark.asyncio
    async def test_async_clear_cache(self):
        """Test async cache clear"""
        from utils.cache import set_cache_async, get_cache_async, clear_cache_async

        await set_cache_async("key1", "value1")
        await set_cache_async("key2", "value2")

        await clear_cache_async()

        result1 = await get_cache_async("key1")
        result2 = await get_cache_async("key2")

        assert result1 is None
        assert result2 is None
