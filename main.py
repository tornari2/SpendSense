"""
Main Entry Point (Root Level)

Alternative entry point at root level.
"""

import uvicorn

if __name__ == "__main__":
    # Use import string to enable reload and workers
    uvicorn.run(
        "spendsense.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

