from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db
from app.api import lesson_routes, research_routes, qc_routes, export_routes

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Lesson Creation Tool backend API with two independent QC layers.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development & frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(lesson_routes.router)
app.include_router(research_routes.router)
app.include_router(qc_routes.router)
app.include_router(export_routes.router)

# Mount frontend static files if directory exists
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": settings.DATABASE_URL.split(":")[0],
    }

@app.get("/", tags=["UI"])
def serve_ui():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "AI-Powered Lesson Creation API is operational",
        "docs_url": "/docs",
        "health_check": "/health",
    }
