import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.session.aiohttp import AiohttpSession # Импортируем сессию для прокси

# --- ТВОИ ДАННЫЕ ---
BOT_TOKEN = "8878271930:AAEnhzbknWmqtE-Khx96p1xR9Yg2"
ADMIN_ID = 8804527509
# -------------------

# Если у тебя есть SOCKS5 или HTTP прокси, можно указать его здесь (например: "http://proxy_ip:port")
# Если оставить без прокси, но убрать долгий polling, можно попробовать через Webhook, 
# но давай сначала подключим сессию с таймаутами:
session = AiohttpSession(timeout=60)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

def init_db():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_user(user_id: int):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

init_db()

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message):
    add_user(message.from_user.id)
    await message.answer("👋 Привет! Ты успешно запустил бота. Администратор может ввести /admin.")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У тебя нет доступа.")
        return
    await message.answer("⚙️ Панель администратора:", reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def cb_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    users = get_all_users()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]])
    await callback.message.edit_text(f"📊 Статистика:\nПользователей в базе: {len(users)}", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "admin_back")
async def cb_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("⚙️ Панель администратора:", reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await callback.message.answer("📢 Введи текст для рассылки всем пользователям (или /cancel для отмены):")
    await callback.answer()

@dp.message(Command("cancel"), AdminStates.waiting_for_broadcast_text)
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.")

@dp.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text
    await state.clear()
    users = get_all_users()
    sent = 0
    status = await message.answer("🚀 Рассылка началась...")
    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await status.edit_text(f"✅ Рассылка завершена! Доставлено: {sent}")

async def main():
    logging.basicConfig(level=logging.INFO)
    # Увеличиваем интервал polling-запросов, чтобы реже дергать сервер и избежать обрывов сокета
    await dp.start_polling(bot, polling_timeout=30)

if __name__ == "__main__":
    asyncio.run(main())
