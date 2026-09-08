from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
  app_env: str = "development"

  database_host: str
  database_port: str
  database_name: str
  database_user: str
  database_password: str

  jwt_secret_key: str
  jwt_algorithm: str = "HS256"
  jwt_access_token_expire_minutes: int = 30

  openai_api_key: str
  openai_base_url: str

  nvidia_api_key: str
  nvidia_base_url: str

  model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
