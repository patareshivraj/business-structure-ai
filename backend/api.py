# backend/api.py - FastAPI application with proper error handling and logging

import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
import os
import re
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from workflow import graph
from utils.cache import get_cache, set_cache
from utils.config_validator import validate_config
from utils.logger import get_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = get_logger(__name__)


# ─── Custom Exception Classes ───────────────────────────────────────────────────────────

class APIError(Exception):
    """Base API exception"""
    def __init__(self, message: str, error_type: str = "api_error", status_code: int = 500):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        super().__init__(self.message)


class ExternalAPIError(APIError):
    """External API (Tavily, Groq, etc.) failure"""
    def __init__(self, message: str):
        super().__init__(message, error_type="external_api_error", status_code=503)


class ValidationError(APIError):
    """Input validation failure"""
    def __init__(self, message: str):
        super().__init__(message, error_type="validation_error", status_code=400)


# ─── Application Lifespan (Startup/Shutdown) ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Business Structure Intelligence API...")

    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed. Exiting.")
        raise SystemExit(1)

    logger.info("Configuration validated successfully")

    yield

    # Shutdown
    logger.info("Shutting down Business Structure Intelligence API...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Business Structure Intelligence API",
    description="AI-powered company organizational structure extraction",
    version="1.0.0",
    lifespan=lifespan
)


# ─── CORS Configuration ───────────────────────────────────────────────────────────────

allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exception Handlers ───────────────────────────────────────────────────────────────

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors"""
    logger.warning(f"API Error: {exc.error_type} - {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "type": exc.error_type,
                "message": exc.message
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "type": "http_error",
                "message": exc.detail
            }
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.exception(f"Unexpected error: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "type": "internal_error",
                "message": "An unexpected error occurred. Please try again later.",
                "details": str(exc) if os.getenv("ENVIRONMENT") == "development" else None
            }
        }
    )


# ─── Pydantic Models ─────────────────────────────────────────────────────────────────

class CompanyRequest(BaseModel):
    name: str

    @field_validator('name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        v = v.strip()

        if len(v) < 1:
            raise ValueError("Company name cannot be empty")

        if len(v) > 200:
            raise ValueError("Company name cannot exceed 200 characters")

        if not re.match(r"^[\w \-\.&]+$", v):
            raise ValueError("Company name contains invalid characters")

        return v


class IntelligenceResponse(BaseModel):
    structure: dict
    company: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, str]


# ─── API Endpoints ─────────────────────────────────────────────────────────────────--

@app.get("/company/{name}")
async def get_company(name: str):
    """Legacy endpoint - redirects to /company/{name}/intelligence"""
    return await get_company_intelligence(name)


@app.get("/company/{name}/intelligence", response_model=IntelligenceResponse)
async def get_company_intelligence(name: str):
    """Get company intelligence including business structure"""

    # Validate input
    try:
        validated_name = CompanyRequest(name=name).name
    except ValueError as e:
        raise ValidationError(str(e))

    key = validated_name.strip().lower()
    logger.info(f"Processing request for company: {validated_name}")

    # Check cache
    cached = get_cache(key)
    if cached:
        logger.info(f"Cache hit for: {validated_name}")
        return IntelligenceResponse(structure=cached, company=validated_name)

    # Process request — run synchronous graph.invoke in a thread to avoid
    # blocking the async event loop
    try:
        result = await asyncio.to_thread(graph.invoke, {"company": validated_name})
        tree = result.get("tree", {})

        if not tree:
            tree = {"name": validated_name, "children": []}

        set_cache(key, tree)
        logger.info(f"Successfully processed: {validated_name}")

        return IntelligenceResponse(structure=tree, company=validated_name)

    except Exception as e:
        logger.exception(f"Error processing request for {validated_name}: {e}")
        raise ExternalAPIError(f"Failed to process company data: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Business Structure Intelligence API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "company_structure": "/company/{name}/intelligence"
        }
    }
