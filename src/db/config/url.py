from pydantic_settings import BaseSettings, SettingsConfigDict

class PostgresURL(BaseSettings):
    DB_HOST: str
    DB_NAME: str
    DB_POSTGRES_USER: str
    DB_POSTGRES_PASSWORD: str
    DB_PORT: int
    model_config = SettingsConfigDict(env_file=".env", extra='ignore', env_file_encoding='utf-8')

    def get_url(self, user: str = None, password: str = None) -> str:
        return f"postgresql+asyncpg://{user or self.DB_POSTGRES_USER}:{password or self.DB_POSTGRES_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"