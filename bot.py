import asyncio
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = "BOT_TOKENINGNI_BU_YERGA_QO'Y"
ADMIN_ID = 123456789  # O'zingizning Telegram ID

bot = Bot(TOKEN)
dp = Dispatcher()

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect("anime.db") as db:
        # Foydalanuvchilar
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
        # Majburiy kanallar
        await db.execute("CREATE TABLE IF NOT EXISTS mandatory_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT)")
        # Anemilar
        await db.execute("""CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, code TEXT UNIQUE, description TEXT, photo TEXT
        )""")
        # Qismlar
        await db.execute("""CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_code TEXT, part_number INTEGER, file_id TEXT
        )""")
        # Reklama
        await db.execute("""CREATE TABLE IF NOT EXISTS reklama (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT, link TEXT,
            end_time INTEGER, daily_time TEXT,
            daily INTEGER DEFAULT 0, active INTEGER DEFAULT 1
        )""")
        # Reklama klik
        await db.execute("""CREATE TABLE IF NOT EXISTS reklama_click (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reklama_id INTEGER, user_id INTEGER
        )""")
        await db.commit()

# ================= STATES =================
class AddAnime(StatesGroup):
    name = State()
    code = State()
    desc = State()
    photo = State()

class AddPart(StatesGroup):
    code = State()
    number = State()
    file = State()

class EditOne(StatesGroup):
    code = State()
    value = State()

class MandatoryState(StatesGroup):
    channel = State()

class SearchAnime(StatesGroup):
    code = State()

class BroadcastState(StatesGroup):
    text = State()

class AddReklama(StatesGroup):
    text = State()
    link = State()
    mode = State()
    datetime_state = State()
    daily_time = State()

# ================= KEYBOARDS =================
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("🔍 Anemi izlash")],
        [KeyboardButton("⭐ Premium anemilar")],
        [KeyboardButton("🆕 Ongion anemilar")]
    ], resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("➕ Yangi anemi qo‘shish")],
        [KeyboardButton("✏️ Nomi o‘zgartirish"), KeyboardButton("✏️ Kodni o‘zgartirish")],
        [KeyboardButton("✏️ Tavsifni o‘zgartirish")],
        [KeyboardButton("📌 Qism qo‘shish")],
        [KeyboardButton("🗑 Anemini o‘chirish")],
        [KeyboardButton("📢 Majburiy obuna qo‘shish"), KeyboardButton("❌ Majburiy obunani o‘chirish")],
        [KeyboardButton("📢 Xabar yuborish"), KeyboardButton("📣 Reklama joylash")],
        [KeyboardButton("📊 Reklama statistikasi")]
    ], resize_keyboard=True
)

# ================= MAJBURIY OBUNA =================
async def check_subscription(user_id):
    async with aiosqlite.connect("anime.db") as db:
        cursor = await db.execute("SELECT channel FROM mandatory_channels")
        channels = await cursor.fetchall()
    if not channels: return True
    not_joined = []
    for ch in channels:
        channel = ch[0]
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left","kicked"]: not_joined.append(channel)
        except: not_joined.append(channel)
    if not_joined:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}")] for ch in not_joined] +
            [[InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]]
        )
        return keyboard
    return True

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message):
    async with aiosqlite.connect("anime.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)",(message.from_user.id,))
        await db.commit()
    sub = await check_subscription(message.from_user.id)
    if sub is not True:
        await message.answer("❗ Botdan foydalanish uchun kanallarga obuna bo‘ling:", reply_markup=sub)
        return
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Admin panel", reply_markup=admin_kb)
    else:
        await message.answer("👋 Xush kelibsiz!", reply_markup=user_kb)

@dp.callback_query(F.data=="check_sub")
async def recheck_sub(callback: types.CallbackQuery):
    sub = await check_subscription(callback.from_user.id)
    if sub is True:
        await callback.message.edit_text("✅ Obuna tasdiqlandi!")
    else:
        await callback.answer("❌ Hali obuna bo‘lmadingiz", show_alert=True)

# ================= ADMIN: MAJBURIY OBUNA =================
@dp.message(F.text=="📢 Majburiy obuna qo‘shish")
async def add_mandatory(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Kanal username kiriting (masalan @kanal):")
    await state.set_state(MandatoryState.channel)

@dp.message(MandatoryState.channel)
async def save_mandatory(message: Message, state: FSMContext):
    async with aiosqlite.connect("anime.db") as db:
        await db.execute("INSERT INTO mandatory_channels (channel) VALUES (?)",(message.text,))
        await db.commit()
    await message.answer("✅ Kanal qo‘shildi")
    await state.clear()

@dp.message(F.text=="❌ Majburiy obunani o‘chirish")
async def delete_mandatory(message: Message):
    if message.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("anime.db") as db:
        await db.execute("DELETE FROM mandatory_channels")
        await db.commit()
    await message.answer("❌ Barcha majburiy kanallar o‘chirildi")

# ================= ADMIN: BROADCAST =================
@dp.message(F.text=="📢 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Xabar matnini kiriting:")
    await state.set_state(BroadcastState.text)

@dp.message(BroadcastState.text)
async def broadcast_send(message: Message, state: FSMContext):
    text = message.text
    async with aiosqlite.connect("anime.db") as db:
        cursor = await db.execute("SELECT id FROM users")
        users = await cursor.fetchall()
    for user in users:
        try: await bot.send_message(user[0], text)
        except: pass
    await message.answer("✅ Xabar barcha foydalanuvchilarga yuborildi")
    await state.clear()

# ================= PREMIUM va ONGION =================
@dp.message(F.text=="⭐ Premium anemilar")
async def premium_anime(message: Message):
    async with aiosqlite.connect("anime.db") as db:
        cursor = await db.execute("SELECT name, code FROM anime WHERE LENGTH(code)=3")
        data = await cursor.fetchall()
    if not data:
        await message.answer("🔹 Premium anemilar mavjud emas")
        return
    text = "\n".join([f"Anemi nomi: {name} Kod {code}" for name,code in data])
    await message.answer(text)

@dp.message(F.text=="🆕 Ongion anemilar")
async def ongion_anime(message: Message):
    async with aiosqlite.connect("anime.db") as db:
        cursor = await db.execute("SELECT name, code FROM anime WHERE LENGTH(code)=5")
        data = await cursor.fetchall()
    if not data:
        await message.answer("🔹 Ongion anemilar mavjud emas")
        return
    text = "\n".join([f"Anemi nomi: {name} Kod {code}" for name,code in data])
    await message.answer(text)

# ================= ANEMI IZLASH =================
@dp.message(F.text=="🔍 Anemi izlash")
async def search_anime_start(message: Message, state: FSMContext):
    await message.answer("Iltimos, anemi kodini kiriting:")
    await state.set_state(SearchAnime.code)

@dp.message(SearchAnime.code)
async def search_anime_code(message: Message, state: FSMContext):
    code = message.text
    async with aiosqlite.connect("anime.db") as db:
        cursor = await db.execute("SELECT name, description, photo FROM anime WHERE code=?",(code,))
        anime = await cursor.fetchone()
        if not anime:
            await message.answer("❌ Bunday anemi topilmadi")
            await state.clear()
            return
        name, desc, photo = anime
        cursor_parts = await db.execute("SELECT part_number, file_id FROM parts WHERE anime_code=? ORDER BY part_number",(code,))
        parts = await cursor_parts.fetchall()
    # Inline tugmalar bilan qismlar
    keyboard = InlineKeyboardMarkup(row_width=5)
    for part_num, file_id in parts:
        keyboard.insert(InlineKeyboardButton(str(part_num), callback_data=f"part_{file_id}"))
    await bot.send_photo(message.chat.id, photo, caption=f"📌 {name}\n\n{desc}", reply_markup=keyboard)
    await state.clear()

@dp.callback_query(F.data.startswith("part_"))
async def send_part(callback: types.CallbackQuery):
    file_id = callback.data.split("_")[1]
    try:
        await bot.send_document(callback.from_user.id, file_id)
    except:
        await callback.answer("❌ Faylni yuborib bo‘lmadi")

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())