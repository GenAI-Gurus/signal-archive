from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    api_key_salt: str
    environment: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
