from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    jwt_secret: str = ""
    data_encryption_key: str = ""
    database_url: str = "sqlite:///./data/ats.db"
    resume_dir: str = "./data/resumes"
    user_llm_api_key: str = ""
    user_llm_base_url: str = ""
    user_llm_model: str = "deepseek-chat"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@localhost"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8000/api/calendar/google/callback"
    public_base_url: str = "http://127.0.0.1:5173"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.jwt_secret or len(s.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET is required and must be at least 32 characters")
    if not s.data_encryption_key:
        raise RuntimeError("DATA_ENCRYPTION_KEY is required")
    return s
