# backend/utils/logger.py - Centralized logging configuration

import logging
import sys
import os
import json
from typing import Any, Dict
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """JSON formatter for production log aggregation"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for development"""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# Track whether root logging has been configured
_logging_configured = False


def setup_logging() -> None:
    """
    Configure the root logger for the application.
    All modules using get_logger(__name__) will inherit this configuration.
    """
    global _logging_configured
    if _logging_configured:
        return

    _logging_configured = True

    # Determine environment
    environment = os.getenv("ENVIRONMENT", "development").lower()
    is_production = environment == "production"

    # Set log level
    level = logging.DEBUG if not is_production else logging.INFO

    # Configure root logger so all child loggers inherit
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers
    if root_logger.handlers:
        return

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Choose formatter based on environment
    if is_production:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(HumanFormatter())

    root_logger.addHandler(console_handler)

    # Set third-party loggers to WARNING to reduce noise
    for noisy_logger in ["urllib3", "requests", "asyncio", "httpx", "httpcore"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


# Configure logging on import
setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance (inherits root configuration)
    """
    return logging.getLogger(name)


# Convenience function for structured logging
def log_request(logger: logging.Logger, method: str, path: str, **kwargs):
    """Log HTTP request with additional context"""
    logger.info(f"{method} {path}", extra={"extra": kwargs})


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """Log exception with context"""
    if context:
        logger.exception(f"{context}: {error}")
    else:
        logger.exception(str(error))