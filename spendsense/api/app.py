"""
Main FastAPI Application

SpendSense API with all routes registered.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from spendsense.api.public import router as public_router
from spendsense.api.operator import router as operator_router
from spendsense.recommend.api import router as recommend_router
from spendsense.ui.routes import router as ui_router
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


# Middleware to disable caching for static files in development
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Only apply to static files
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Add no-cache middleware BEFORE mounting static files
app.add_middleware(NoCacheMiddleware)

# Mount static files for UI
app.mount("/static", StaticFiles(directory="spendsense/ui/static"), name="static")

# Register routers
app.include_router(public_router)
app.include_router(operator_router)
app.include_router(recommend_router)
app.include_router(ui_router)  # Operator UI routes (includes root "/" route)


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

