import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import load_dotenv

# Импорт из amo_crm_chat
from amo_crm_chat import find_or_create_chat, send_message_to_amocrm

load_dotenv()  # Загружаем .env
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env! Создайте файл с переменными.")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@dp.message(Command('start'))
async def start_handler(message: types.Message):
    user = message.from_user
    tg_id = str(user.id)
    name = user.full_name or 'User'
    username = user.username

    amocrm_id = await find_or_create_chat(tg_id, name=name, username=username)
    if amocrm_id:
        await message.reply('Чат готов. Можете отправлять сообщения.')
    else:
        await message.reply('Ошибка создания чата.')

@dp.message()
async def message_handler(message: types.Message):
    user = message.from_user
    tg_id = str(user.id)
    text = message.text
    name = user.full_name or 'User'
    username = user.username

    amocrm_id = await find_or_create_chat(tg_id, name=name, username=username)
    if not amocrm_id:
        await message.reply('Ошибка создания чата. Попробуйте /start.')
        return

    success = await send_message_to_amocrm(amocrm_id, tg_id, text)
    if success:
        await message.reply('Сообщение отправлено в amoCRM.')
    else:
        await message.reply('Ошибка отправки.')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
