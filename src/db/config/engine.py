from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from db.config.url import PostgresURL

class EngineDB:

    def __init__(self, user: str = None, password: str = None) -> None:
        url = PostgresURL().get_url()
        self.async_engine = create_async_engine(
            url=url,
            echo=False
        )

    def get_engine(self) -> AsyncSession:
        session = async_sessionmaker(self.async_engine, expire_on_commit=False)
        return session()