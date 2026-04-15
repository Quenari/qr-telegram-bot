import os
import asyncio
import qrcode
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# Загрузка токена
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    print("Добавьте переменную окружения BOT_TOKEN на Render")
    exit(1)

print(f"✅ Токен загружен: {BOT_TOKEN[:15]}...")

# Создаём бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_colors = {}

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для создания QR-кодов.\n\n"
        "📝 Просто напиши текст или ссылку — я сделаю QR-код.\n"
        "🎨 /color — изменить цвет QR-кода\n"
        "❓ /help — справка"
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "🔧 Команды бота:\n\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/color — изменить цвет QR-кода\n\n"
        "💡 Просто отправь текст — я сделаю QR!"
    )

@dp.message(Command("color"))
async def color_command(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⚫ Чёрный", callback_data="color_black")],
        [types.InlineKeyboardButton(text="🔵 Синий", callback_data="color_blue")],
        [types.InlineKeyboardButton(text="🔴 Красный", callback_data="color_red")],
        [types.InlineKeyboardButton(text="🟢 Зелёный", callback_data="color_green")],
    ])
    await message.answer("🎨 Выберите цвет QR-кода:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("color_"))
async def process_color(callback: types.CallbackQuery):
    colors = {
        "color_black": "чёрный",
        "color_blue": "синий", 
        "color_red": "красный",
        "color_green": "зелёный",
    }
    color_code = {
        "color_black": "black",
        "color_blue": "blue",
        "color_red": "red",
        "color_green": "green",
    }
    
    color_name = colors.get(callback.data, "чёрный")
    color_value = color_code.get(callback.data, "black")
    
    user_colors[callback.from_user.id] = color_value
    await callback.answer(f"Цвет изменён на {color_name}")
    await callback.message.answer(f"✅ Теперь ваши QR-коды будут {color_name} цвета!")

@dp.message()
async def generate_qr(message: types.Message):
    text = message.text
    if not text or text.startswith('/'):
        return
    
    fill_color = user_colors.get(message.from_user.id, "black")
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=fill_color, back_color="white")
    
    os.makedirs("output", exist_ok=True)
    file_path = "output/qr_temp.png"
    img.save(file_path)
    
    photo = FSInputFile(file_path)
    await message.answer_photo(
        photo, 
        caption=f"✅ QR-код создан!\n📝 Данные: {text[:100]}..."
    )
    
    os.remove(file_path)

# Запуск бота
async def main():
    print("🚀 Бот запускается...")
    print("🤖 Бот готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
