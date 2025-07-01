from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


engine = create_async_engine("sqlite+aiosqlite:///teletask.db")
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
