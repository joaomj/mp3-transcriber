import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Add the 'src' directory to the Python path to allow module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app.security import limiter
from src.app.tasks import shutdown_scheduler, start_scheduler
from src.app.transcription import router as transcription_router

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """
    Manages the application's lifespan events.
    Starts the cleanup scheduler on startup and shuts it down on exit.
    """
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="Vercel Whisper Transcriber",
    description="A serverless web application for audio transcription using OpenAI's Whisper API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add state and exception handlers for rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# Mount the static directory to serve the UI
# The path is relative to this file's location
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include the transcription API router
app.include_router(transcription_router)


@app.get("/", response_class=HTMLResponse)
async def read_root() -> HTMLResponse:
    """Serves the main user interface page."""
    try:
        with open(os.path.join(static_dir, "index.html")) as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>UI files not found</h1>", status_code=500)
