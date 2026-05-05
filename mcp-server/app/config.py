"""Application configuration from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mongodb_uri: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URI")
    mongodb_db: str = Field(default="shopping_mcp", alias="MONGODB_DB")

    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_public_collection: str = Field(
        default="public_catalog_docs", alias="QDRANT_PUBLIC_COLLECTION"
    )
    qdrant_private_collection: str = Field(
        default="private_member_docs", alias="QDRANT_PRIVATE_COLLECTION"
    )

    public_base_url: str = Field(default="http://localhost:8000", alias="PUBLIC_BASE_URL")

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    bedrock_model_id: str | None = Field(default=None, alias="BEDROCK_MODEL_ID")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_session_token: str | None = Field(default=None, alias="AWS_SESSION_TOKEN")

    mock_oauth_client_id: str = Field(default="demo-client", alias="MOCK_OAUTH_CLIENT_ID")
    mock_oauth_client_secret: str = Field(default="demo-secret", alias="MOCK_OAUTH_CLIENT_SECRET")

    session_cookie_name: str = Field(default="mcp_session", alias="SESSION_COOKIE_NAME")

    data_dir: str = Field(default="app/data", alias="DATA_DIR")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
