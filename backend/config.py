from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging
import logging.handlers
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_logging():
    """Setup comprehensive logging configuration"""
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs (DEBUG level)
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Special handler for matching logs
    matching_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "matching.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3
    )
    matching_handler.setLevel(logging.DEBUG)
    matching_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    matching_handler.setFormatter(matching_formatter)
    
    # Create matching logger
    matching_logger = logging.getLogger("matching")
    matching_logger.setLevel(logging.DEBUG)
    matching_logger.addHandler(matching_handler)
    matching_logger.propagate = False  # Don't propagate to root logger
    
    # Special handler for buckeye scraper logs
    buckeye_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "buckeye.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3
    )
    buckeye_handler.setLevel(logging.DEBUG)
    buckeye_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    buckeye_handler.setFormatter(buckeye_formatter)
    
    # Create buckeye logger
    buckeye_logger = logging.getLogger("buckeye")
    buckeye_logger.setLevel(logging.DEBUG)
    buckeye_logger.addHandler(buckeye_handler)
    buckeye_logger.propagate = False  # Don't propagate to root logger
    
    logging.info("Logging configuration initialized")

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

# Setup logging when config is imported
setup_logging() 