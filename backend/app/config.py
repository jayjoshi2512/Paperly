from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables or .env file.
    """
    # Database
    DATABASE_URL: str = Field(..., description="MySQL async connection string (mysql+aiomysql://...)")
    
    # Qdrant
    QDRANT_URL: str = Field("http://qdrant:6333", description="Qdrant vector store URL")
    
    # Observability (Langfuse)
    LANGFUSE_HOST: str = Field("http://langfuse:3000", description="Langfuse self-hosted URL")
    LANGFUSE_PUBLIC_KEY: str = Field(..., description="Langfuse public key")
    LANGFUSE_SECRET_KEY: str = Field(..., description="Langfuse secret key")
    
    # External APIs
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key")
    COHERE_API_KEY: str = Field(..., description="Cohere API Key for reranking")
    GROQ_API_KEY: str = Field("", description="Groq API Key for fast LLM inference")
    
    # JWT & Auth
    JWT_SECRET: str = Field(..., description="Secret key for JWT encoding")
    JWT_ALGORITHM: str = Field("HS256", description="Algorithm for JWT encoding")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, description="Access token expiration in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, description="Refresh token expiration in days")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
