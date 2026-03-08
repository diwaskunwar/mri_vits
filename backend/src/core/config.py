import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Candor Dust"
    
    # SQLite database for simplicity (demo mode)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./candor_dust.db"
    )
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "candor-dust-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Model service URL (Ray Serve)
    MODEL_SERVICE_URL: str = os.getenv("MODEL_SERVICE_URL", "http://localhost:8001")
    
    class Config:
        env_file = ".env"


settings = Settings()

