import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import os
import json
from dotenv import load_dotenv

# Импорт из amo_crm_chat
from amo_crm_chat import find_or_create_chat, send_message_to_amocrm

load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
DATA_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data'))
USER_FILE  = os.path.join(DATA_DIR, 'user_conversations.json')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env! Создайте файл с переменными.")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def find_user_by_tg_id(tg_id):
    if not os.path.exists(USER_FILE):
        return None

    try:
        with open(USER_FILE, encoding='utf-8') as f:
            users: list[dict] = json.load(f)
    except (json.JSONDecodeError, OSError):
        # Файл пустой или битый — считаем, что пользователя нет
        return None

    for user in users:
        if user.get('tg_id') == tg_id:
            return user
    return None

@dp.message(Command('start'))
async def start_handler(message: types.Message):
    user = message.from_user
    tg_id = str(user.id)
    name = user.full_name or 'User'
    username = user.username

    welcome_text = 'Чат создан из /start.'

    amocrm_id = await find_or_create_chat(tg_id, name=name, username=username, welcome_text=welcome_text)
    if not amocrm_id:
        await message.reply('Ошибка создания чата.')

@dp.message()
async def message_handler(message: types.Message):
    user = message.from_user
    tg_id = str(user.id)
    text = message.text
    name = user.full_name or 'User'
    username = user.username

    amocrm_id = await find_or_create_chat(tg_id, name=name, username=username, welcome_text='Чат создан из сообщения' )
    if not amocrm_id:
        await message.reply('Ошибка создания чата. Попробуйте /start.')
        return

    if not (find_user_by_tg_id(tg_id) == None):
        success = await send_message_to_amocrm(amocrm_id, tg_id, text)
        if not success:
            await message.reply('Ошибка отправки.')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
