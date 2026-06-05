from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS — dashboard (origens específicas)
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # CORS — widget embeddable (aceita qualquer origem por padrão)
    # Em produção, restringir para os domínios dos clientes se necessário
    WIDGET_CORS_ORIGINS: List[str] = ["*"]

    # Claude API
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "nexusai"

    # M2: Voyage AI — embeddings
    VOYAGE_API_KEY: str = ""

    # M2: Storage — volume local em dev
    UPLOAD_DIR: str = "/app/uploads"

    # M5: Storage — R2/S3 (prod)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "nexusai-uploads"
    AWS_ENDPOINT_URL: str = ""  # R2: https://<account-id>.r2.cloudflarestorage.com
    AWS_REGION: str = "auto"

    # M2: Chunking
    CHUNK_SIZE_TOKENS: int = 512
    CHUNK_OVERLAP_TOKENS: int = 50

    # M3: RAG
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.7
    RAG_HISTORY_MESSAGES: int = 6   # últimas N mensagens incluídas no prompt
    RAG_MAX_TOKENS: int = 1024       # max_tokens da resposta do Claude

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
