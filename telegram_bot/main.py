import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

import os
import json
from dotenv import load_dotenv
import aiofiles
from datetime import datetime

# Импорт из amo_crm_chat
from user_db import *
from main import create_chat_amo


load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data'))
USER_FILE = os.path.join(DATA_DIR, 'user_conversations.json')
BASE_AVATAR_URL = os.environ.get('BASE_AVATAR_URL', 'https://flowsynk.ru')

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)



async def download_user_avatar(bot: Bot, user_id: int):
    """Загружает аватар, сохраняя исходный тип файла, и возвращает URL."""
    try:
        profile_photos = await bot.get_user_profile_photos(user_id, limit=1)
        if profile_photos.total_count == 0:
            return None

        photo = profile_photos.photos[0][-1]
        file = await bot.get_file(photo.file_id)
        
        # Определяем расширение файла из пути, который даёт Telegram
        file_ext = os.path.splitext(file.file_path)[1]
        if not file_ext:
            file_ext = '.jpg' # Безопасный дефолт для фото
        
        # Формируем имя файла с правильным расширением
        filename = datetime.now().strftime(f"result%Y%m%d%H%M%S{file_ext}")
        
        profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data', 'profile_picture'))
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)
        
        file_path = os.path.join(profile_dir, filename)
        
        await bot.download_file(file.file_path, destination=file_path)
        
        # Возвращаем полный URL (убедитесь, что ваш сервер настроен)
        return f'{filename}'
    except Exception as e:
        print(f"Ошибка загрузки аватара: {e}")
        return None

async def process_user_message(message: types.Message ,welcome_text = None):
    user = message.from_user
    tg_id = str(user.id)
    check_user = find_user_by_tg_id(tg_id) 
    if check_user == None:
        name = user.full_name or 'User'
        username = user.username
        
        # Загружаем новый аватар
        avatar_url = await download_user_avatar(bot, user.id)  

        if avatar_url == None:
            final_avatar = 'https://example.com/avatar.png'
        else:
            final_avatar = f'{BASE_AVATAR_URL}/profile_picture/{avatar_url}'


        if welcome_text == None:
            user_text = message.text
        else:
            user_text = welcome_text    
        
        amocrm_id = await create_chat(
            tg_id, 
            name=name, 
            username=username, 
            welcome_text=user_text, 
            avatar=final_avatar
        )
        if not amocrm_id:
            await message.reply('Ошибка создания или обновления чата.')
            return
        create_user (amocrm_id = amocrm_id,
                    tg_id = tg_id,
                    name = name,
                    username = username,
                    avatar = avatar_url,
                    email = None,
                    phone = None
                    )
    else:
        await send_message_to_amocrm(check_user['amocrm_id'], tg_id, message.text)
    


@dp.message(Command('start'))
async def start_handler(message: types.Message):
    await process_user_message(message, welcome_text='Чат создан из /start.')


@dp.message()
async def message_handler(message: types.Message):
    await process_user_message(message)

async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
