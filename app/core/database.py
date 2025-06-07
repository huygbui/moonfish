from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import settings

engine = create_async_engine(str(settings.sqlalchemy_url))
async_session = async_sessionmaker(engine, expire_on_commit=False)
