from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    openai_api_key: str
    api_key_salt: str
    environment: str = "development"
    resend_api_key: str = ""
    jwt_secret: str = "dev-secret-change-in-prod"
    fernet_key: str = ""

settings = Settings()
