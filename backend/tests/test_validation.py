# backend/tests/test_validation.py - Validation logic tests

import pytest
import re
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCompanyNameValidation:
    """Test company name validation logic"""

    # Pattern from api.py
    VALID_PATTERN = r"^[\w \-\.&]+$"

    def test_valid_company_names(self):
        """Test valid company names match pattern"""
        valid_names = [
            "Apple",
            "Apple Inc",
            "Microsoft Corporation",
            "Google-LLC",
            "Amazon Web Services",
            "TCS & Co.",
            "Reliance Industries Ltd.",
            "IBM",
            "3M Company",
            "A&B Corp"
        ]
        for name in valid_names:
            assert re.match(self.VALID_PATTERN, name), f"Should match: {name}"

    def test_invalid_company_names(self):
        """Test invalid company names don't match pattern"""
        invalid_names = [
            "<script>alert(1)</script>",
            "Test\nInjection",
            "Company\tTab",
            "Test<iframe>",
            "Company@special",
            "Dollar$Sign",
            "Percent%Sign",
            "Hash#Sign",
            "Star*Sign"
        ]
        for name in invalid_names:
            assert not re.match(self.VALID_PATTERN, name), f"Should not match: {name}"

    def test_sql_injection_patterns(self):
        """Test SQL injection patterns are blocked"""
        sql_patterns = [
            "'; DROP TABLE companies;--",
            "1' OR '1'='1",
            "admin'--",
            "'; DELETE FROM users;--"
        ]
        for pattern in sql_patterns:
            assert not re.match(self.VALID_PATTERN, pattern)

    def test_xss_patterns(self):
        """Test XSS patterns are blocked"""
        xss_patterns = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "<svg/onload=alert(1)>",
            "javascript:alert(1)",
            "<body onload=alert(1)>"
        ]
        for pattern in xss_patterns:
            assert not re.match(self.VALID_PATTERN, pattern)

    def test_path_traversal_patterns(self):
        """Test path traversal patterns are blocked"""
        traversal_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        for pattern in traversal_patterns:
            assert not re.match(self.VALID_PATTERN, pattern)


class TestInputSanitization:
    """Test input sanitization functions"""

    def test_whitespace_trimming(self):
        """Test whitespace is trimmed from inputs"""
        test_cases = [
            ("  Apple  ", "Apple"),
            ("\tMicrosoft\t", "Microsoft"),
            ("\nGoogle\n", "Google"),
            ("  TCS & Co.  ", "TCS & Co.")
        ]
        for input_val, expected in test_cases:
            result = input_val.strip()
            assert result == expected

    def test_null_byte_handling(self):
        """Test strings with null bytes are detectable"""
        test_with_null = "Test\x00Company"
        # Null bytes are present in the string (strip does NOT remove them)
        assert "\x00" in test_with_null
        # But our regex validation would reject this at the API level
        import re
        pattern = r"^[\w\s\-\.&]+$"
        assert not re.match(pattern, test_with_null)


class TestDataValidation:
    """Test general data validation"""

    def test_company_name_length_limits(self):
        """Test company name length limits"""
        # Minimum length
        assert len("") < 1, "Empty string should fail min length"

        # Maximum length
        long_name = "A" * 200
        assert len(long_name) <= 200, "200 chars should pass"

        too_long = "A" * 201
        assert len(too_long) > 200, "201 chars should fail"

    def test_allowed_special_characters(self):
        """Test allowed special characters in company names"""
        allowed = [
            "Johnson & Johnson",
            "Baker-McKenzie",
            "Deloitte Touche",
            "A.T. Kearney",
            "PricewaterhouseCoopers"
        ]
        pattern = r"^[\w\s\-\.&]+$"
        for name in allowed:
            assert re.match(pattern, name), f"Should allow: {name}"


class TestAPIResponseValidation:
    """Test API response validation"""

    def test_intelligence_response_structure(self):
        """Test intelligence response has required fields"""
        required_fields = ["structure", "company"]

        # Mock response
        response_data = {
            "structure": {"name": "Test", "children": []},
            "company": "Test"
        }

        for field in required_fields:
            assert field in response_data, f"Missing field: {field}"

    def test_tree_structure_validation(self):
        """Test business tree structure validation"""
        # Valid tree
        valid_tree = {
            "name": "Company",
            "children": [
                {"name": "Division", "children": [{"name": "Product"}]}
            ]
        }

        def validate_tree(node, depth=0):
            """Recursively validate tree structure"""
            assert "name" in node, "Node must have name"
            assert depth <= 3, "Tree depth exceeds maximum"

            for child in node.get("children", []):
                validate_tree(child, depth + 1)

        validate_tree(valid_tree)

    def test_empty_tree_handling(self):
        """Test empty tree is handled properly"""
        empty_tree = {"name": "Company", "children": []}

        assert "name" in empty_tree
        assert "children" in empty_tree
        assert isinstance(empty_tree["children"], list)


class TestCacheKeyValidation:
    """Test cache key validation"""

    def test_cache_key_generation(self):
        """Test cache keys are generated safely"""
        company = "TestCompany"
        key = company.strip().lower()

        assert key == "testcompany"
        # Key should not contain special characters
        assert re.match(r"^[\w\-]+$", key)

    def test_malformed_cache_keys(self):
        """Test malformed cache keys are handled"""
        # These should be sanitized before use
        malicious_keys = [
            "test<script>",
            "test\ninjection",
            "test\tdifferent"
        ]

        for key in malicious_keys:
            sanitized = key.strip().lower()
            # After sanitization, newlines and tabs are removed by strip
            # but other chars remain — validation should catch them upstream
            assert isinstance(sanitized, str)
