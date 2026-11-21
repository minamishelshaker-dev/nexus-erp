"""
Nexus ERP - Main Application Entry Point
=========================================

This is the main FastAPI application entry point that configures
the entire ERP system including middleware, routers, and startup.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import time
from typing import Callable

from app.core.config import settings
from app.core.database import db_manager

# Import all endpoints
from app.api.v1.endpoints import auth, customers
from app.api.v1.endpoints import accounts, journal_entries, reports
from app.api.v1.endpoints import stock_moves
from app.api.v1.endpoints import sales, purchase
from app.api.v1.endpoints import ai, manufacturing
from app.api.v1.endpoints import workflows
from app.api.v1.endpoints import billing
from app.api.v1.endpoints import hr
from app.api.v1.endpoints import projects
from app.api.v1.endpoints import pos
from app.api.v1.endpoints import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Initialize database connection
    await db_manager.init_db()
    logger.info("Database connection initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await db_manager.close_db()
    logger.info("Database connection closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
# Nexus ERP - Enterprise Resource Planning System

A comprehensive, modern ERP system built with FastAPI and React.

## Core Modules

### Accounting Module
- **Chart of Accounts**: Full hierarchical account structure
- **Journal Entries**: Double-entry bookkeeping with automatic validation
- **Financial Reports**: Trial Balance, Income Statement, Balance Sheet

### Inventory Module
- **Products**: Full product management with variants and UOM
- **Warehouses**: Multi-warehouse support with locations
- **Stock Moves**: Complete stock movement tracking
- **Inventory Adjustments**: Periodic stock counting

### CRM Module
- **Customers**: Customer management with contacts and addresses
- **Leads**: Lead tracking and qualification
- **Opportunities**: Sales pipeline management

## Authentication

All API endpoints require authentication via JWT Bearer token.

1. Obtain token via `/api/v1/auth/login`
2. Include token in Authorization header: `Bearer <token>`
3. Refresh token via `/api/v1/auth/refresh`
    """,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ========================================
# Middleware Configuration
# ========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    """Add X-Process-Time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# ========================================
# Exception Handlers
# ========================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": errors,
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error" if settings.ENVIRONMENT == "production" else str(exc),
            }
        }
    )


# ========================================
# Health Check Endpoints
# ========================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint."""
    try:
        async with db_manager.get_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        )

    return {
        "status": "ready",
        "services": {
            "database": "healthy",
            "api": "healthy",
        }
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
    }


# ========================================
# API Router Registration
# ========================================

from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")

# Authentication
api_v1_router.include_router(auth.router)

# CRM Module
api_v1_router.include_router(customers.router)

# Accounting Module
api_v1_router.include_router(accounts.router)
api_v1_router.include_router(journal_entries.router)
api_v1_router.include_router(reports.router)

# Inventory Module
api_v1_router.include_router(stock_moves.router)

# Sales Module
api_v1_router.include_router(sales.router)

# Purchase Module
api_v1_router.include_router(purchase.router)

# AI Module
api_v1_router.include_router(ai.router)

# Manufacturing Module
api_v1_router.include_router(manufacturing.router)

# Workflows Module
api_v1_router.include_router(workflows.router)

# Billing Module
api_v1_router.include_router(billing.router)

# HR Module
api_v1_router.include_router(hr.router)

# Projects Module
api_v1_router.include_router(projects.router)

# POS Module
api_v1_router.include_router(pos.router)

# Settings Module
api_v1_router.include_router(settings.router)

# Include API router in app
app.include_router(api_v1_router)


# ========================================
# Development Utilities
# ========================================

if settings.DEBUG:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Show current configuration (debug mode only)."""
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "database_pool_size": settings.DATABASE_POOL_SIZE,
            "multi_tenant": settings.MULTI_TENANT_ENABLED,
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
