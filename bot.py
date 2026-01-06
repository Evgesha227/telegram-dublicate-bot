import os
import sqlite3
import hashlib
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ContentType

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN not found in environment variables")

bot = Bot(token=TOKEN)
dp = Dispatcher()

os.makedirs("media", exist_ok=True)

# --- БАЗА ---
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


def get_hash(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


# --- START ---
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Я слежу за дубликатами 👀")


# --- ФОТО ---
@dp.message(F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message):
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
        await message.delete()
        os.remove(path)
        return

    cursor.execute(
        "INSERT INTO hashes (hash, chat_id, message_id) VALUES (?, ?, ?)",
        (img_hash, message.chat.id, message.message_id)
    )
    conn.commit()


# --- FORGET ---
@dp.message(Command("forget"))
async def forget_photo(message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply("Ответь командой /forget на сообщение с фото 📸")
        return

    replied = message.reply_to_message

    cursor.execute(
        "DELETE FROM hashes WHERE chat_id=? AND message_id=?",
        (replied.chat.id, replied.message_id)
    )
    conn.commit()

    await message.reply("Окей, я забыл это фото 🧠❌")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())