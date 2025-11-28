from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # App
    app_name: str = os.getenv("APP_NAME")
    app_version: str = os.getenv("APP_VERSION")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL")
    test_database_url: str = os.getenv("TEST_DATABASE_URL")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL")
    
    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Email
    from_email: str = os.getenv("FROM_EMAIL")
    
    # Resend API
    resend_api_key: str = os.getenv("RESEND_API_KEY")
    
    # CORS
    cors_origins: List[str] = ["https://furuplus.com", "http://localhost:3000"]
    
    print("cors_origins", cors_origins)
    
    # Celery
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND")
    
    # Stripe
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY")
    stripe_publishable_key: str = os.getenv("STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # Backend URL
    backend_url: str = os.getenv("BACKEND_URL")
    
    #OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    
    #Polygon API
    polygon_stocks_api_key: str = os.getenv("POLYGON_STOCKS_API_KEY")
    polygon_currencies_api_key: str=os.getenv("POLYGON_CURRENCIES_API_KEY")
    # polygon_options_api_key: str = os.getenv("POLYGON_OPTIONS_API_KEY")
    
    #Environment
    environment: str = os.getenv("ENVIRONMENT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


settings = Settings()