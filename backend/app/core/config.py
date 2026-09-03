from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./dev.sqlite3"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_storage_bucket: str = "source-imports"
    supabase_model_storage_bucket: str = "model-artifacts"
    cors_allowed_origins: str = "http://localhost:3000"
    app_env: str = "development"
    demo_mode: bool = True
    log_level: str = "INFO"
    analytics_random_seed: int = 42
    max_upload_bytes: int = 15_000_000
    supabase_jwt_issuer: str = ""
    demo_storage_path: str = ".demo_data/source-imports"
    demo_model_storage_path: str = ".demo_data/model-artifacts"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def jwt_issuer(self) -> str:
        return self.supabase_jwt_issuer or f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_runtime_configuration(settings: Settings) -> None:
    if settings.app_env.strip().lower() not in {"production", "prod"}:
        return
    missing = []
    if settings.demo_mode:
        missing.append("DEMO_MODE=false")
    if not settings.database_url or settings.database_url.lower().startswith("sqlite"):
        missing.append("a PostgreSQL DATABASE_URL")
    if not settings.supabase_url.startswith("https://"):
        missing.append("SUPABASE_URL")
    if not settings.supabase_service_role_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError(
            "Production configuration is incomplete: " + ", ".join(missing) + "."
        )
