import os
import sqlite3
import hashlib
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ContentType

# ===== TOKEN =====
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not found in environment variables")

# ===== BOT =====
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== FILES =====
os.makedirs("media", exist_ok=True)

# ===== DATABASE =====
conn = sqlite3.connect("hashes.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS hashes (
    hash TEXT,
    chat_id INTEGER,
    message_id INTEGER
)
""")
conn.commit()


# ===== HASH FUNCTION =====
def get_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


# ===== COMMON PHOTO LOGIC =====
async def process_photo(message: Message):
    photo = message.photo[-1]
    file = await bot.download(photo.file_id)

    path = f"media/{photo.file_unique_id}.jpg"
    with open(path, "wb") as f:
        f.write(file.read())

    img_hash = get_hash(path)

    cursor.execute(
        "SELECT 1 FROM hashes WHERE hash=? AND chat_id=?",
        (img_hash, message.chat.id)
    )
    exists = cursor.fetchone()

    if exists:
        try:
            await message.delete()
        except:
            pass
        os.remove(path)
        return

    cursor.execute(
        "INSERT INTO hashes (hash, chat_id, message_id) VALUES (?, ?, ?)",
        (img_hash, message.chat.id, message.message_id)
    )
    conn.commit()


# ===== START =====
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Я слежу за дубликатами 👀")


# ===== PHOTO (PRIVATE / GROUPS) =====
@dp.message(F.content_type == ContentType.PHOTO)
async def handle_message_photo(message: Message):
    await process_photo(message)


# ===== PHOTO (CHANNEL) =====
@dp.channel_post(F.photo)
async def handle_channel_photo(message: Message):
    await process_photo(message)


# ===== FORGET