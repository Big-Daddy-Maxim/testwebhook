import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from amo_crm_chat import user_conversations, create_chat_from_telegram, send_message_to_amocrm
import json
import os
from dotenv import load_dotenv

load_dotenv() 

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env! Создайте файл с переменными.")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

CONVERSATIONS_FILE = 'conversations_map.json'  # {conv_id: tg_user_id}

def load_conversations() -> dict:
    if os.path.exists(CONVERSATIONS_FILE):
        with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {}

def save_conversations(data: dict) -> None:
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)

conversations_map = load_conversations()

@dp.message(Command('start'))
async def start_handler(message: types.Message):
    user = message.from_user
    user_id = str(user.id)
    if user_id in user_conversations:
        await message.reply('Чат уже создан. Можете отправлять сообщения.')
        return
    conv_id = await create_chat_from_telegram(user_id, user.full_name or 'User', user.username, 'default@example.com')
    if conv_id:
        await message.reply('Чат создан. Теперь вы можете общаться с amoCRM.')
        conversations_map[conv_id] = user_id  # Сохраняем conv_id -> user_id
        save_conversations(conversations_map)
    else:
        await message.reply('Ошибка создания чата.')

@dp.message()
async def message_handler(message: types.Message):
    user = message.from_user
    user_id = str(user.id)
    text = message.text
    if user_id not in user_conversations:
        conv_id = await create_chat_from_telegram(user_id, user.full_name or 'User', user.username, 'default@example.com')
        if not conv_id:
            await message.reply('Ошибка создания чата. Попробуйте /start.')
            return
        conversations_map[conv_id] = user_id  # Сохраняем mapping здесь тоже
        save_conversations(conversations_map)
    conv_id = user_conversations[user_id]
    success = await send_message_to_amocrm(conv_id, user_id, text)
    if success:
        await message.reply('Сообщение отправлено в amoCRM.')
    else:
        await message.reply('Ошибка отправки.')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
