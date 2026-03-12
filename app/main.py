from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router
from config.settings import settings
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Local LLM-based Email and Message Assistant",
    version=settings.APP_VERSION
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Mount static files correctly
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_dashboard():
    # Provide the path relative to the project root
    return FileResponse(os.path.join("static", "index.html"))

@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 Starting {settings.APP_NAME}")
    logger.info(f"🤖 Model: {settings.DEFAULT_MODEL}")