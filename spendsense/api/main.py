"""
Main Entry Point for SpendSense API

Run the FastAPI application with uvicorn.
"""

import uvicorn

if __name__ == "__main__":
    # Use import string to enable reload and workers
    uvicorn.run(
        "spendsense.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload for development
    )

