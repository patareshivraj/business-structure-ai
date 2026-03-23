# backend/tests/test_api.py - API endpoint tests

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app, CompanyRequest, IntelligenceResponse


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_cache():
    """Mock cache for testing"""
    with patch('api.get_cache') as mock_get, \
         patch('api.set_cache') as mock_set:
        mock_get.return_value = None
        mock_set.return_value = None
        yield {"get": mock_get, "set": mock_set}


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_check(self, client):
        """Test /health endpoint returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data


class TestCompanyValidation:
    """Test company name validation"""

    def test_valid_company_name(self):
        """Test valid company names pass validation"""
        valid_names = [
            "Apple Inc",
            "Microsoft",
            "Google",
            "Amazon-Web-Services",
            "IBM Corporation",
            "TCS & Sons",
            "Reliance Industries Ltd."
        ]
        for name in valid_names:
            request = CompanyRequest(name=name)
            assert request.name == name.strip()

    def test_empty_company_name(self):
        """Test empty company name is rejected"""
        with pytest.raises(ValueError) as exc_info:
            CompanyRequest(name="")
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_only_name(self):
        """Test whitespace-only name is rejected"""
        with pytest.raises(ValueError) as exc_info:
            CompanyRequest(name="   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_company_name_too_long(self):
        """Test overly long company names are rejected"""
        with pytest.raises(ValueError) as exc_info:
            CompanyRequest(name="A" * 201)
        assert "cannot exceed 200 characters" in str(exc_info.value)

    def test_company_name_with_invalid_chars(self):
        """Test names with invalid characters are rejected"""
        invalid_names = [
            "Test<script>alert(1)</script>",
            "Company@#$$%",
            "Test\nInjection",
            "Company\tTab",
            "Company| Pipe"
        ]
        for name in invalid_names:
            with pytest.raises(ValueError) as exc_info:
                CompanyRequest(name=name)
            assert "invalid characters" in str(exc_info.value)


class TestIntelligenceEndpoint:
    """Test company intelligence endpoint"""

    def test_intelligence_endpoint_success(self, client, mock_cache):
        """Test successful intelligence retrieval"""
        # Mock the workflow graph
        with patch('api.graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "company": "TestCompany",
                "tree": {
                    "name": "TestCompany",
                    "children": [
                        {"name": "Products", "children": [{"name": "Product A"}]}
                    ]
                }
            }

            response = client.get("/company/TestCompany/intelligence")
            assert response.status_code == 200
            data = response.json()
            assert data["company"] == "TestCompany"
            assert "structure" in data
            assert data["structure"]["name"] == "TestCompany"

    def test_intelligence_returns_cached(self, client):
        """Test cached data is returned when available"""
        cached_tree = {
            "name": "CachedCompany",
            "children": [{"name": "Cached"}]
        }

        with patch('api.get_cache') as mock_get:
            mock_get.return_value = cached_tree

            response = client.get("/company/CachedCompany/intelligence")
            assert response.status_code == 200
            data = response.json()
            assert data["structure"] == cached_tree

    def test_intelligence_validation_error(self, client):
        """Test invalid company name returns error response"""
        response = client.get("/company/!@#$%/intelligence")
        # Should get an error (either 400 from our handler or 422 from FastAPI)
        assert response.status_code in (400, 422)
        data = response.json()
        # Our custom handler returns {"success": false, "error": {...}}
        # FastAPI validation returns {"detail": [...]}
        assert "error" in data or "detail" in data

    def test_legacy_endpoint_redirects(self, client, mock_cache):
        """Test legacy /company/{name} endpoint works"""
        with patch('api.graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "company": "Legacy",
                "tree": {"name": "Legacy", "children": []}
            }

            response = client.get("/company/Legacy")
            assert response.status_code == 200


class TestIntelligenceResponse:
    """Test IntelligenceResponse model"""

    def test_valid_response(self):
        """Test valid response model"""
        response = IntelligenceResponse(
            company="Test",
            structure={"name": "Test", "children": []}
        )
        assert response.company == "Test"
        assert "structure" in response.model_dump()
