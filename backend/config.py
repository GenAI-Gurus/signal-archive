from pydantic import model_validator
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

    @model_validator(mode="after")
    def check_secrets_in_production(self) -> "Settings":
        if self.environment != "development":
            if self.jwt_secret == "dev-secret-change-in-prod":
                raise ValueError("JWT_SECRET must be set in non-development environments")
            if not self.fernet_key:
                raise ValueError("FERNET_KEY must be set in non-development environments")
        return self

settings = Settings()
