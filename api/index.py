import os
import sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Add the 'src' directory to the Python path to allow module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app.security import limiter
from src.app.tasks import start_scheduler, shutdown_scheduler
from src.app.transcription import router as transcription_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifespan events.
    Starts the cleanup scheduler on startup and shuts it down on exit.
    """
    start_scheduler()
    yield
    shutdown_scheduler()

app = FastAPI(lifespan=lifespan)

# Add state and exception handlers for rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount the static directory to serve the UI
# The path is relative to this file's location
static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include the transcription API router
app.include_router(transcription_router)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main user interface page."""
    with open(os.path.join(static_dir, 'index.html')) as f:
        return HTMLResponse(content=f.read())
