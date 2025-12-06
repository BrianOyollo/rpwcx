import asyncio
import os
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from psycopg2 import errors


import utils
from routers.auth_router import auth_router


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(auth_router)
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Bot Active")
    asyncio.run(main())