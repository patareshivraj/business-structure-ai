# backend/utils/config_validator.py - Startup configuration validation

import os
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ConfigError:
    """Configuration error details"""
    key: str
    message: str
    severity: str = "error"  # error, warning


class ConfigValidator:
    """
    Validates required environment variables and API keys at startup.
    Fails fast with clear messages if required configuration is missing.
    """

    # Required configuration keys (must be present)
    REQUIRED: List[str] = [
        "TAVILY_API_KEY",
        "GROQ_API_KEY",
    ]

    # Optional configuration keys (will use defaults if missing)
    OPTIONAL: List[str] = [
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_DB",
        "REDIS_PASSWORD",
        "REDIS_PREFIX",
        "CACHE_TTL",
        "CACHE_MAX_SIZE",
        "ALLOWED_ORIGINS",
        "HOST",
        "PORT",
        "ENVIRONMENT",
    ]

    def __init__(self):
        self.errors: List[ConfigError] = []
        self.warnings: List[ConfigError] = []

    def validate(self) -> bool:
        """
        Validate all configuration.

        Returns:
            True if validation passes, False otherwise
        """
        self._check_required()
        self._check_optional()
        self._check_api_key_format()

        if self.errors:
            self._print_errors()
            return False

        if self.warnings:
            self._print_warnings()

        return True

    def _check_required(self):
        """Check that all required environment variables are set"""
        for key in self.REQUIRED:
            value = os.getenv(key)
            if not value:
                self.errors.append(ConfigError(
                    key=key,
                    message=f"Required environment variable '{key}' is not set. "
                            f"Please add {key} to your .env file."
                ))
            elif not value.strip():
                self.errors.append(ConfigError(
                    key=key,
                    message=f"Required environment variable '{key}' is empty. "
                            f"Please provide a valid value."
                ))

    def _check_optional(self):
        """Check optional configuration and set defaults"""
        # Redis configuration validation
        redis_port = os.getenv("REDIS_PORT")
        if redis_port:
            try:
                port = int(redis_port)
                if port < 1 or port > 65535:
                    self.warnings.append(ConfigError(
                        key="REDIS_PORT",
                        message=f"REDIS_PORT {port} is out of valid range (1-65535). Using default.",
                        severity="warning"
                    ))
            except ValueError:
                self.warnings.append(ConfigError(
                    key="REDIS_PORT",
                    message=f"REDIS_PORT '{redis_port}' is not a valid integer. Using default.",
                    severity="warning"
                ))

        # Cache TTL validation
        cache_ttl = os.getenv("CACHE_TTL")
        if cache_ttl:
            try:
                ttl = int(cache_ttl)
                if ttl < 0:
                    self.warnings.append(ConfigError(
                        key="CACHE_TTL",
                        message=f"CACHE_TTL must be positive. Using default (3600).",
                        severity="warning"
                    ))
            except ValueError:
                self.warnings.append(ConfigError(
                    key="CACHE_TTL",
                    message=f"CACHE_TTL '{cache_ttl}' is not a valid integer. Using default.",
                    severity="warning"
                ))

    def _check_api_key_format(self):
        """Validate API key formats"""
        # Check Groq API key format (should be a valid format)
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key and len(groq_key) < 10:
            self.warnings.append(ConfigError(
                key="GROQ_API_KEY",
                message="GROQ_API_KEY seems unusually short. Please verify it's correct.",
                severity="warning"
            ))

        # Check Tavily API key format
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key and len(tavily_key) < 10:
            self.warnings.append(ConfigError(
                key="TAVILY_API_KEY",
                message="TAVILY_API_KEY seems unusually short. Please verify it's correct.",
                severity="warning"
            ))

    def _print_errors(self):
        """Print validation errors"""
        print("\n" + "="*60)
        print("CONFIGURATION VALIDATION FAILED")
        print("="*60)
        for error in self.errors:
            print(f"  ❌ {error.key}")
            print(f"     {error.message}")
        print("="*60)
        print("\nTo fix this, add the missing variables to your .env file.")
        print("See .env.example for reference.\n")

    def _print_warnings(self):
        """Print validation warnings"""
        print("\n" + "-"*60)
        print("CONFIGURATION WARNINGS")
        print("-"*60)
        for warning in self.warnings:
            print(f"  ⚠️  {warning.key}: {warning.message}")
        print("-"*60 + "\n")

    def get_config_summary(self) -> Dict[str, str]:
        """Get a summary of current configuration for debugging"""
        summary = {}
        for key in self.REQUIRED + self.OPTIONAL:
            value = os.getenv(key)
            if value:
                # Mask sensitive values
                if key.endswith("_KEY") or key.endswith("_PASSWORD"):
                    summary[key] = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
                else:
                    summary[key] = value
            else:
                summary[key] = "<not set>"
        return summary


def validate_config() -> bool:
    """
    Convenience function to validate configuration.

    Returns:
        True if validation passes, False otherwise
    """
    validator = ConfigValidator()
    return validator.validate()


if __name__ == "__main__":
    # Test validation
    print("Running configuration validation...")
    if validate_config():
        print("✅ Configuration valid!")
    else:
        print("❌ Configuration validation failed")