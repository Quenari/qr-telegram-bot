import os
import asyncio
import qrcode
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загрузка токена
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

print(f"✅ Токен загружен: {BOT_TOKEN[:15]}...")

# Создаём бота с хранилищем для состояний
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

user_colors = {}

# === СОСТОЯНИЯ ДЛЯ ДИАЛОГОВ ===
class WiFiForm(StatesGroup):
    ssid = State()      # название сети
    password = State()  # пароль
    encryption = State() # тип шифрования

class ContactForm(StatesGroup):
    name = State()      # имя
    phone = State()     # телефон
    email = State()     # email

class GeoForm(StatesGroup):
    latitude = State()  # широта
    longitude = State() # долгота

# === КЛАВИАТУРА ГЛАВНОГО МЕНЮ ===
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Текст / URL")],
            [KeyboardButton(text="📶 Wi-Fi"), KeyboardButton(text="👤 Контакт (vCard)")],
            [KeyboardButton(text="📍 Геолокация"), KeyboardButton(text="🎨 Цвет QR")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard

# === ОБРАБОТЧИКИ КОМАНД ===

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для создания QR-кодов.\n\n"
        "Выберите тип QR-кода из меню ниже:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "🔧 Команды бота:\n\n"
        "/start — главное меню\n"
        "/text — создать QR из текста/ссылки\n"
        "/wifi — создать QR для подключения к Wi-Fi\n"
        "/contact — создать QR для контакта\n"
        "/geo — создать QR для геолокации\n"
        "/color — изменить цвет QR-кода\n\n"
        "📱 После создания QR-кода просто наведите камеру телефона!"
    )

@dp.message(Command("text"))
async def text_command(message: types.Message):
    await message.answer("✏️ Напишите текст или ссылку:")

@dp.message(Command("wifi"))
async def wifi_command(message: types.Message, state: FSMContext):
    await state.set_state(WiFiForm.ssid)
    await message.answer(
        "📶 Создание QR-кода для Wi-Fi\n\n"
        "Введите название сети (SSID):"
    )

@dp.message(Command("contact"))
async def contact_command(message: types.Message, state: FSMContext):
    await state.set_state(ContactForm.name)
    await message.answer(
        "👤 Создание QR-кода для контакта\n\n"
        "Введите имя контакта:"
    )

@dp.message(Command("geo"))
async def geo_command(message: types.Message, state: FSMContext):
    await state.set_state(GeoForm.latitude)
    await message.answer(
        "📍 Создание QR-кода для геолокации\n\n"
        "Введите широту (например: 55.7558):"
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

# === ОБРАБОТЧИК КНОПОК МЕНЮ ===
@dp.message(lambda message: message.text == "📝 Текст / URL")
async def menu_text(message: types.Message):
    await message.answer("✏️ Напишите текст или ссылку:")

@dp.message(lambda message: message.text == "📶 Wi-Fi")
async def menu_wifi(message: types.Message, state: FSMContext):
    await state.set_state(WiFiForm.ssid)
    await message.answer("Введите название сети (SSID):")

@dp.message(lambda message: message.text == "👤 Контакт (vCard)")
async def menu_contact(message: types.Message, state: FSMContext):
    await state.set_state(ContactForm.name)
    await message.answer("Введите имя контакта:")

@dp.message(lambda message: message.text == "📍 Геолокация")
async def menu_geo(message: types.Message, state: FSMContext):
    await state.set_state(GeoForm.latitude)
    await message.answer("Введите широту (например: 55.7558):")

@dp.message(lambda message: message.text == "🎨 Цвет QR")
async def menu_color(message: types.Message):
    await color_command(message)

@dp.message(lambda message: message.text == "❓ Помощь")
async def menu_help(message: types.Message):
    await help_command(message)

# === ОБРАБОТЧИК ЦВЕТА ===
@dp.callback_query(lambda c: c.data.startswith("color_"))
async def process_color(callback: types.CallbackQuery):
    colors = {
        "color_black": ("чёрный", "black"),
        "color_blue": ("синий", "blue"),
        "color_red": ("красный", "red"),
        "color_green": ("зелёный", "green"),
    }
    color_name, color_value = colors.get(callback.data, ("чёрный", "black"))
    
    user_colors[callback.from_user.id] = color_value
    await callback.answer(f"Цвет изменён на {color_name}")
    await callback.message.answer(f"✅ Теперь ваши QR-коды будут {color_name} цвета!")

# === ГЕНЕРАЦИЯ QR-КОДОВ ===
def generate_qr_image(data: str, fill_color: str) -> str:
    """Создаёт QR-код и возвращает путь к файлу"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=fill_color, back_color="white")
    
    os.makedirs("output", exist_ok=True)
    file_path = "output/qr_temp.png"
    img.save(file_path)
    return file_path

# === ОБРАБОТЧИК Wi-Fi ===
@dp.message(WiFiForm.ssid)
async def process_wifi_ssid(message: types.Message, state: FSMContext):
    await state.update_data(ssid=message.text)
    await state.set_state(WiFiForm.encryption)
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="WPA/WPA2", callback_data="wpa"),
         types.InlineKeyboardButton(text="WEP", callback_data="wep")],
        [types.InlineKeyboardButton(text="Без пароля", callback_data="nopass")]
    ])
    await message.answer("Выберите тип шифрования:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data in ["wpa", "wep", "nopass"])
async def process_wifi_encryption(callback: types.CallbackQuery, state: FSMContext):
    enc_map = {"wpa": "WPA", "wep": "WEP", "nopass": "nopass"}
    await state.update_data(encryption=enc_map[callback.data])
    
    if callback.data == "nopass":
        await finish_wifi(callback, state)
    else:
        await state.set_state(WiFiForm.password)
        await callback.message.answer("Введите пароль от Wi-Fi:")
    await callback.answer()

@dp.message(WiFiForm.password)
async def process_wifi_password(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text)
    await finish_wifi(message, state)

async def finish_wifi(event, state: FSMContext):
    data = await state.get_data()
    ssid = data.get("ssid")
    encryption = data.get("encryption")
    password = data.get("password", "")
    
    # Формируем строку для Wi-Fi QR-кода
    if encryption == "nopass":
        wifi_string = f"WIFI:S:{ssid};T:nopass;;"
    else:
        wifi_string = f"WIFI:T:{encryption};S:{ssid};P:{password};;"
    
    fill_color = user_colors.get(event.from_user.id, "black")
    file_path = generate_qr_image(wifi_string, fill_color)
    
    photo = FSInputFile(file_path)
    await event.message.answer_photo(
        photo,
        caption=f"✅ QR-код для Wi-Fi сети: {ssid}\n📱 Отсканируйте для подключения!"
    )
    os.remove(file_path)
    await state.clear()
    await event.message.answer("Что ещё хотите создать?", reply_markup=get_main_keyboard())

# === ОБРАБОТЧИК КОНТАКТА (vCard) ===
@dp.message(ContactForm.name)
async def process_contact_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ContactForm.phone)
    await message.answer("Введите номер телефона:")

@dp.message(ContactForm.phone)
async def process_contact_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(ContactForm.email)
    await message.answer("Введите email (или '-' чтобы пропустить):")

@dp.message(ContactForm.email)
async def process_contact_email(message: types.Message, state: FSMContext):
    email = message.text
    if email == "-":
        email = ""
    
    await state.update_data(email=email)
    data = await state.get_data()
    
    # Формируем vCard
    vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{data['name']}
TEL:{data['phone']}
"""
    if email:
        vcard += f"EMAIL:{email}\n"
    vcard += "END:VCARD"
    
    fill_color = user_colors.get(message.from_user.id, "black")
    file_path = generate_qr_image(vcard, fill_color)
    
    photo = FSInputFile(file_path)
    await message.answer_photo(
        photo,
        caption=f"✅ QR-код для контакта: {data['name']}\n📱 Отсканируйте, чтобы сохранить в телефон!"
    )
    os.remove(file_path)
    await state.clear()
    await message.answer("Что ещё хотите создать?", reply_markup=get_main_keyboard())

# === ОБРАБОТЧИК ГЕОЛОКАЦИИ ===
@dp.message(GeoForm.latitude)
async def process_geo_lat(message: types.Message, state: FSMContext):
    try:
        lat = float(message.text)
        await state.update_data(latitude=lat)
        await state.set_state(GeoForm.longitude)
        await message.answer("Введите долготу (например: 37.6173):")
    except ValueError:
        await message.answer("❌ Ошибка! Введите число (например: 55.7558)")

@dp.message(GeoForm.longitude)
async def process_geo_lon(message: types.Message, state: FSMContext):
    try:
        lon = float(message.text)
        data = await state.get_data()
        lat = data.get("latitude")
        
        # Формируем geo URI
        geo_string = f"geo:{lat},{lon}"
        
        fill_color = user_colors.get(message.from_user.id, "black")
        file_path = generate_qr_image(geo_string, fill_color)
        
        photo = FSInputFile(file_path)
        await message.answer_photo(
            photo,
            caption=f"✅ QR-код для геолокации:\n📍 Широта: {lat}\n📍 Долгота: {lon}"
        )
        os.remove(file_path)
        await state.clear()
        await message.answer("Что ещё хотите создать?", reply_markup=get_main_keyboard())
    except ValueError:
        await message.answer("❌ Ошибка! Введите число (например: 37.6173)")

# === ОБРАБОТЧИК ТЕКСТА ===
@dp.message()
async def generate_qr(message: types.Message):
    text = message.text
    if not text or text.startswith('/') or text in ["📝 Текст / URL", "📶 Wi-Fi", "👤 Контакт (vCard)", "📍 Геолокация", "🎨 Цвет QR", "❓ Помощь"]:
        return
    
    fill_color = user_colors.get(message.from_user.id, "black")
    file_path = generate_qr_image(text, fill_color)
    
    photo = FSInputFile(file_path)
    await message.answer_photo(
        photo, 
        caption=f"✅ QR-код создан!\n📝 Данные: {text[:100]}..."
    )
    os.remove(file_path)

# === ЗАПУСК ===
async def main():
    print("🚀 Бот запускается...")
    print("🤖 Бот готов к работе!")
    print("📱 Доступные типы QR: текст, Wi-Fi, контакты, геолокация")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
