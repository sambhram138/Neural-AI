import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "AI Lesson Creation Tool"
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./lesson_creator.db"
    
    # LLM Settings
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    
    # Research API Keys
    TAVILY_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    
    # Storage
    UPLOAD_DIR: str = str(BASE_DIR.parent / "uploads")
    EXPORT_DIR: str = str(BASE_DIR.parent / "exports")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
