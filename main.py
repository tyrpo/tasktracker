import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.handlers import router_handlers
from database.models import Base
from database.init_database import engine

bot = Bot(token="7906729088:AAHZgznzpmZ6vR5vKyCDBuU-NuXjDzDh0dU")
dp = Dispatcher()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    await init_db()
    dp.include_router(router_handlers)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
