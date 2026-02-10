import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = "7569301938:AAEuwjohpRgBPm4zSbKhdpy87lyDEFK8bW8"
ADMIN_ID = 737309777

bot = Bot(TOKEN)
dp = Dispatcher()

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect("anime.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            code TEXT UNIQUE,
            description TEXT,
            photo TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_code TEXT,
            part_number INTEGER,
            file_id TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS mandatory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT
        )
        """)
        await db.commit()

# ================= KEYBOARDS =================
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Anemi izlash")],
        [KeyboardButton(text="⭐ Premium anemilar")],
        [KeyboardButton(text="🆕 Ongion anemilar")]
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Yangi anemi qo‘shish")],
        [KeyboardButton(text="✏️ Nomi o‘zgartirish")],
        [KeyboardButton(text="✏️ Kodni o‘zgartirish")],
        [KeyboardButton(text="✏️ Tavsifni o‘zgartirish")],
        [KeyboardButton(text="📌 Qism qo‘shish")],
        [KeyboardButton(text="🗑 Anemini o‘chirish")],
        [KeyboardButton(text="📢 Majburiy obuna qo‘shish")],
        [KeyboardButton(text="❌ Majburiy obunani o‘chirish")]
    ],
    resize_keyboard=True
)

# ================= STATES =================
class AddAnime(StatesGroup):
    name = State()
    code = State()
    desc = State()
    photo = State()

class EditOne(StatesGroup):
    code = State()
    value = State()

class AddPart(StatesGroup):
    code = State()
    number = State()
    file = State()

class MandatoryState(StatesGroup):
    channel = State()

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Admin panel", reply_markup=admin_kb)
    else:
        await message.answer("👋 Xush kelibsiz!", reply_markup=user_kb)

# ================= ADD ANIME =================
@dp.message(F.text == "➕ Yangi anemi qo‘shish")
async def add_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Anemi nomi:")
    await state.set_state(AddAnime.name)

@dp.message(AddAnime.name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Anemi kodi:")
    await state.set_state(AddAnime.code)

@dp.message(AddAnime.code)
async def add_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Tavsifi:")
    await state.set_state(AddAnime.desc)

@dp.message(AddAnime.desc)
async def add_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Rasm yuboring:")
    await state.set_state(AddAnime.photo)

@dp.message(AddAnime.photo, F.photo)
async def add_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect("anime.db") as db:
        await db.execute(
            "INSERT INTO anime (name, code, description, photo) VALUES (?, ?, ?, ?)",
            (data["name"], data["code"], data["desc"], message.photo[-1].file_id)
        )
        await db.commit()
    await message.answer("✅ Saqlandi", reply_markup=admin_kb)
    await state.clear()

# ================= EDIT FUNCTIONS =================
@dp.message(F.text.in_(["✏️ Nomi o‘zgartirish","✏️ Kodni o‘zgartirish","✏️ Tavsifni o‘zgartirish"]))
async def edit_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.update_data(action=message.text)
    await message.answer("Anemi kodi:")
    await state.set_state(EditOne.code)

@dp.message(EditOne.code)
async def edit_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Yangi qiymat:")
    await state.set_state(EditOne.value)

@dp.message(EditOne.value)
async def edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = "name" if "Nomi" in data["action"] else "code" if "Kod" in data["action"] else "description"
    async with aiosqlite.connect("anime.db") as db:
        await db.execute(f"UPDATE anime SET {field}=? WHERE code=?", (message.text, data["code"]))
        await db.commit()
    await message.answer("✅ Yangilandi", reply_markup=admin_kb)
    await state.clear()

# ================= ADD PART =================
@dp.message(F.text == "📌 Qism qo‘shish")
async def part_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Anemi kodi:")
    await state.set_state(AddPart.code)

@dp.message(AddPart.code)
async def part_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Qism raqami:")
    await state.set_state(AddPart.number)

@dp.message(AddPart.number)
async def part_number(message: Message, state: FSMContext):
    await state.update_data(number=int(message.text))
    await message.answer("Video yoki fayl yuboring:")
    await state.set_state(AddPart.file)

@dp.message(AddPart.file, F.video | F.document)
async def part_file(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id if message.video else message.document.file_id
    async with aiosqlite.connect("anime.db") as db:
        await db.execute(
            "INSERT INTO parts (anime_code, part_number, file_id) VALUES (?, ?, ?)",
            (data["code"], data["number"], file_id)
        )
        await db.commit()
    await message.answer("✅ Qism qo‘shildi", reply_markup=admin_kb)
    await state.clear()

# ================= DELETE ANIME =================
@dp.message(F.text == "🗑 Anemini o‘chirish")
async def delete_anime(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("O‘chirish uchun anemi kodi:")
    await state.set_state(EditOne.code)

@dp.message(EditOne.code)
async def confirm_delete(message: Message, state: FSMContext):
    async with aiosqlite.connect("anime.db") as db:
        await db.execute("DELETE FROM anime WHERE code=?", (message.text,))
        await db.execute("DELETE FROM parts WHERE anime_code=?", (message.text,))
        await db.commit()
    await message.answer("🗑 O‘chirildi", reply_markup=admin_kb)
    await state.clear()

# ================= MANDATORY =================
@dp.message(F.text == "📢 Majburiy obuna qo‘shish")
async def mand_add(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Kanal @username:")
    await state.set_state(MandatoryState.channel)

@dp.message(MandatoryState.channel)
async def mand_save(message: Message, state: FSMContext):
    async with aiosqlite.connect("anime.db") as db:
        await db.execute("INSERT INTO mandatory (channel) VALUES (?)", (message.text,))
        await db.commit()
    await message.answer("✅ Qo‘shildi", reply_markup=admin_kb)
    await state.clear()

@dp.message(F.text == "❌ Majburiy obunani o‘chirish")
async def mand_del(message: Message):
    async with aiosqlite.connect("anime.db") as db:
        await db.execute("DELETE FROM mandatory")
        await db.commit()
    await message.answer("❌ O‘chirildi", reply_markup=admin_kb)

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

