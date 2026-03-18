from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    HEADLESS_MODE: int
    QUANTITY_INN: int
    USER_AGENT: str 
    URL_FEDRESURS: str
    URL_KADARBITR: str
    
    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

env = Env()
