import asyncio
import hashlib
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

TOKEN = "8236629542:AAGKRISV7s1GcaQjuPfuhi42rAEnwFXoPa8"

DB_NAME = "hashes.db"
MEDIA_DIR = "media"

os.makedirs(MEDIA_DIR, exist_ok=True)

# --- База данных ---
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT UNIQUE
)
""")
conn.commit()

# --- Бот ---
bot = Bot(token=TOKEN)
dp = Dispatcher()


def get_file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


async def process_media(message: Message):
    file = None

    if message.photo:
        file = message.photo[-1]
    elif message.video:
        file = message.video
    else:
        return

    file_info = await bot.get_file(file.file_id)
    file_path = os.path.join(MEDIA_DIR, file.file_id)

    await bot.download_file(file_info.file_path, file_path)

    file_hash = get_file_hash(file_path)

    cursor.execute("SELECT 1 FROM files WHERE hash=?", (file_hash,))
    exists = cursor.fetchone()

    if exists:
        try:
            await message.delete()
        except:
            pass
    else:
        cursor.execute("INSERT INTO files (hash) VALUES (?)", (file_hash,))
        conn.commit()


# --- /start ТОЛЬКО в личке ---
@dp.message(CommandStart(), F.chat.type == "private")
async def start_private(message: Message):
    await message.answer("Я слежу за дубликатами 👀")


# --- ЛИЧНЫЕ ЧАТЫ ---
@dp.message(F.chat.type == "private")
async def private_media(message: Message):
    await process_media(message)


# --- КАНАЛ ---
@dp.channel_post()
async def channel_media(message: Message):
    await process_media(message)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())