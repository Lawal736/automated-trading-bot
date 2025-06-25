from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.v1.api import api_router
from app.core.database import init_db
from app.models import *  # Import all models to register them

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    setup_logging()
    logger.info("Starting up...")
    init_db()  # Call synchronously since init_db is now synchronous
    logger.info(f"CORS ALLOWED_ORIGINS at startup: {settings.ALLOWED_HOSTS}")
    yield
    # Shutdown
    logger.info("Shutting down...")
    # Cleanup resources if needed


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Automated Trading Bot Platform API",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Log the full validation error
        errors = exc.errors()
        logger.error(f"Validation error: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": [
                {"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in errors
            ]},
        )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS,
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {
            "message": "Automated Trading Bot Platform API",
            "version": "1.0.0",
            "status": "running"
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_application() 