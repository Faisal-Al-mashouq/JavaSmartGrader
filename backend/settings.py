import os
from pathlib import Path
from typing import Literal

import boto3
from pydantic_settings import BaseSettings

_backend_dir = Path(__file__).resolve().parent
ENV_FILE = _backend_dir / (
    ".env.local" if os.getenv("APP_ENV", "").strip().lower() == "local" else ".env"
)


class Settings(BaseSettings):
    app_env: Literal["local", "dev", "prod"] = "local"
    log_level: str = "INFO"
    fastapi_port: int = 8000
    jwt_secret_key: str = "your-super-secret-jwt-key"

    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"
    async_database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    )
    db_port: int = 5432

    queue_namespace: str = "jsg.v1"
    redis_endpoint: str = "redis://localhost:6379"
    redis_port: int = 6379

    main_queue: str = "MainJobQueue"
    main_max_concurrency: int = 5

    azure_ocr_endpoint: str = "https://gpfirsttrydoc.cognitiveservices.azure.com/"
    api_azure: str = "API_AZURE"
    api_google_vision: str = "API_GOOGLE_VISION"
    ocr_queue: str = "OCRJobQueue"
    ocr_max_concurrency: int = 5

    gemini_model: str = "gemini-3.1-flash-lite-preview"

    sandbox_queue: str = "SandboxJobQueue"
    sandbox_max_concurrency: int = 5

    ai_grading_queue: str = "AIGradingJobQueue"
    api_key: str = "API_KEY"
    model: str = "MODEL"
    ai_grading_max_concurrency: int = 5

    storage_backend: str = "s3"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "java-smart-grader-bucket"
    s3_region: str = "us-east-1"

    api_gemini: str = "API_GEMINI"
    api_azure: str = "API_AZURE"
    api_google_vision: str = "API_GOOGLE_VISION"
    api_openai: str = "API_OPENAI"
    api_groq: str = "API_GROQ"
    api_claude: str = "API_CLAUDE"
    api_deepseek: str = "API_DEEPSEEK"

    anthropic_api_key: str = "ANTHROPIC_API_KEY"
    openai_api_key: str = "OPENAI_API_KEY"
    google_api_key: str = "GOOGLE_API_KEY"
    groq_api_key: str = "GROQ_API_KEY"
    mistral_api_key: str = "MISTRAL_API_KEY"
    xai_api_key: str = "XAI_API_KEY"
    deepseek_api_key: str = "DEEPSEEK_API_KEY"
    dashscope_api_key: str = "DASHSCOPE_API_KEY"

    sandbox_host_tmp_path: str = ""

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
    }


settings = Settings()

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    region_name=settings.s3_region,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
)
