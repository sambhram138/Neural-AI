from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import lesson_routes

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

@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": settings.DATABASE_URL.split(":")[0],
    }

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "AI-Powered Lesson Creation API is operational",
        "docs_url": "/docs",
        "health_check": "/health",
    }
