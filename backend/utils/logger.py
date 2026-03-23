# backend/utils/logger.py - Centralized logging configuration

import logging
import sys
import os
import json
from typing import Any, Dict
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for production log aggregation"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
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


def setup_logging(name: str = "bsi") -> logging.Logger:
    """
    Configure and return a logger for the application.
    
    Args:
        name: Logger name (default: "bsi" for Business Structure Intelligence)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Determine environment
    environment = os.getenv("ENVIRONMENT", "development").lower()
    is_production = environment == "production"
    
    # Set log level
    level = logging.DEBUG if not is_production else logging.INFO
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Choose formatter based on environment
    if is_production:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(HumanFormatter())
    
    logger.addHandler(console_handler)
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return logger


# Create application logger
app_logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Logger instance
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