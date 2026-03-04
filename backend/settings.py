from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    app_env: str = "local"

    redis_endpoint: str = "redis://redis:6379"
    redis_port: int = 6379
    max_concurrency: int = 10

    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"
    async_database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    )
    db_port: int = 5432

    jwt_secret_key: str = "your-super-secret-jwt-key"

    fastapi_port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

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

    azure_ocr_endpoint: str = "https://gpfirsttrydoc.cognitiveservices.azure.com/"
    gemini_model: str = "gemini-3.1-flash-preview"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
