from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", cli_parse_args=True)
    PORT: int = 5012
    HOST: str = "0.0.0.0"
    DEBUG: bool = False


Config = Settings()
