"""
Main FastAPI Application

SpendSense API with all routes registered.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from spendsense.api.public import router as public_router
from spendsense.api.operator import router as operator_router
from spendsense.recommend.api import router as recommend_router
from spendsense.api.exceptions import ConsentRequiredError, UserNotFoundError, RecommendationNotFoundError


# Create FastAPI app
app = FastAPI(
    title="SpendSense API",
    description="Financial education platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(public_router)
app.include_router(operator_router)
app.include_router(recommend_router)


# Root endpoint
@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "SpendSense API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=400,
        content={"error": "Bad Request", "detail": str(exc)}
    )


@app.exception_handler(ConsentRequiredError)
async def consent_required_handler(request, exc):
    """Handle consent required errors."""
    return JSONResponse(
        status_code=403,
        content={"error": "Consent Required", "detail": exc.detail}
    )


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request, exc):
    """Handle user not found errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "User Not Found", "detail": exc.detail}
    )


@app.exception_handler(RecommendationNotFoundError)
async def recommendation_not_found_handler(request, exc):
    """Handle recommendation not found errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "Recommendation Not Found", "detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "detail": exc.errors()}
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle generic HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP Exception", "detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)}
    )

