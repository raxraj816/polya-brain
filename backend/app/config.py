"""Runtime settings for the PolyaBrain backend."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings shared by the local backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PolyaBrain Backend"
    app_version: str = "0.1.0"
    environment: str = Field(default="local", alias="POLYABRAIN_ENV")
    log_level: str = Field(default="INFO", alias="POLYABRAIN_LOG_LEVEL")
    secret_key: str = Field(default="", alias="POLYABRAIN_SECRET_KEY")
    session_run_timeout_seconds: int = Field(
        default=900,
        ge=1,
        alias="POLYABRAIN_SESSION_RUN_TIMEOUT_SECONDS",
    )
    clarification_timeout_seconds: int = Field(
        default=86400,
        ge=60,
        alias="POLYABRAIN_CLARIFICATION_TIMEOUT_SECONDS",
    )
    database_url: str = Field(
        default="postgresql+psycopg://polyabrain:polyabrain@localhost:5432/polyabrain",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    openrouter_api_key: SecretStr = Field(default=SecretStr(""), alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_model: str = Field(default="", alias="OPENROUTER_MODEL")
    openrouter_fallback_models: str = Field(
        default="",
        alias="OPENROUTER_FALLBACK_MODELS",
    )
    openrouter_app_url: str | None = Field(default=None, alias="OPENROUTER_APP_URL")
    openrouter_app_title: str = Field(default="PolyaBrain", alias="OPENROUTER_APP_TITLE")
    openrouter_data_collection: str = Field(
        default="deny",
        pattern="^(allow|deny)$",
        alias="OPENROUTER_DATA_COLLECTION",
    )
    openrouter_zdr: bool = Field(default=False, alias="OPENROUTER_ZDR")
    openrouter_require_parameters_for_json: bool = Field(
        default=True,
        alias="OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON",
    )
    search_provider: str = Field(default="", alias="SEARCH_PROVIDER")
    search_api_key: SecretStr = Field(default=SecretStr(""), alias="SEARCH_API_KEY")
    search_base_url: str = Field(
        default="https://api.search.brave.com/res/v1/web/search",
        alias="SEARCH_BASE_URL",
    )
    research_max_queries: int = Field(default=3, ge=1, le=20, alias="RESEARCH_MAX_QUERIES")
    research_max_results_per_query: int = Field(
        default=5,
        ge=1,
        le=20,
        alias="RESEARCH_MAX_RESULTS_PER_QUERY",
    )
    research_max_total_candidates: int = Field(
        default=15,
        ge=1,
        le=100,
        alias="RESEARCH_MAX_TOTAL_CANDIDATES",
    )
    cognitive_max_model_calls: int = Field(
        default=12,
        ge=0,
        le=100,
        alias="COGNITIVE_MAX_MODEL_CALLS",
    )
    cognitive_max_external_calls: int = Field(
        default=3,
        ge=0,
        le=100,
        alias="COGNITIVE_MAX_EXTERNAL_CALLS",
    )
    cognitive_max_input_tokens: int = Field(
        default=120_000,
        ge=0,
        le=10_000_000,
        alias="COGNITIVE_MAX_INPUT_TOKENS",
    )
    cognitive_max_output_tokens: int = Field(
        default=16_000,
        ge=0,
        le=1_000_000,
        alias="COGNITIVE_MAX_OUTPUT_TOKENS",
    )
    cognitive_max_normalized_cost: float = Field(
        default=6.0,
        ge=0.0,
        le=1_000.0,
        alias="COGNITIVE_MAX_NORMALIZED_COST",
    )
    cognitive_max_duration_ms: float = Field(
        default=300_000.0,
        ge=0.0,
        le=3_600_000.0,
        alias="COGNITIVE_MAX_DURATION_MS",
    )
    artifact_allowed_roots: str = Field(default="", alias="ARTIFACT_ALLOWED_ROOTS")
    artifact_max_file_bytes: int = Field(
        default=1_000_000,
        ge=1,
        le=10_000_000,
        alias="ARTIFACT_MAX_FILE_BYTES",
    )
    code_execution_enabled: bool = Field(default=False, alias="CODE_EXECUTION_ENABLED")
    code_execution_image: str = Field(
        default=(
            "python:3.14-alpine@sha256:"
            "a1321512d6a287428c50dcdf2ab3857761127e03a23b1f648e9c1c0de59288f8"
        ),
        alias="CODE_EXECUTION_IMAGE",
    )
    code_execution_timeout_seconds: float = Field(
        default=5.0,
        ge=0.5,
        le=30.0,
        alias="CODE_EXECUTION_TIMEOUT_SECONDS",
    )
    code_execution_memory_mb: int = Field(
        default=64,
        ge=32,
        le=512,
        alias="CODE_EXECUTION_MEMORY_MB",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so app startup and tests share one config object."""
    return Settings()
