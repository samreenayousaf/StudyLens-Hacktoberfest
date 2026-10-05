from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "StudyLens API"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = "sqlite:///./studylens.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
