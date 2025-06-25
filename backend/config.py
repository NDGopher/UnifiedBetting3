from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Unified Betting App"
    DEBUG: bool = True
    VERSION: str = "0.1.0"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # POD Service settings
    POD_REFRESH_INTERVAL: int = 1800  # 30 minutes
    POD_SESSION_TIMEOUT: int = 3600   # 1 hour
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./betting_app.db"
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # CORS settings
    CORS_ORIGINS: list = ["http://localhost:3000"]  # Frontend URL
    
    # Chrome profile settings for PTO scraper
    chrome_user_data_dir: str = "C:/Users/steph/OneDrive/Desktop/ProdProjects/PropBuilderEV/pto_chrome_profile"
    chrome_profile_dir: str = "Profile 1"
    
    class Config:
        env_file = ".env"

# Create settings instance
settings = Settings() 