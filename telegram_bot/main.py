# telegram_bot/main.py

import asyncio
import os
import json
import logging
import aiohttp
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Импорт из общего модуля bd_connector
from user_db import find_user_by_tg_id, create_user

# --- Настройка логгера ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

# --- Конфигурация ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
BASE_AVATAR_URL = os.environ.get('BASE_AVATAR_URL', 'https://flowsynk.ru')
AMO_SEND_URL = "http://amo_send:8000"  # URL внутреннего сервиса amo_send

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


async def download_user_avatar(bot: Bot, user_id: int):
    """Загружает аватар и возвращает его имя файла."""
    try:
        profile_photos = await bot.get_user_profile_photos(user_id, limit=1)
        if profile_photos.total_count == 0:
            logging.warning(f"У пользователя {user_id} нет аватара.")
            return None

        photo = profile_photos.photos[0][-1]
        file = await bot.get_file(photo.file_id)
        
        file_ext = os.path.splitext(file.file_path)[1] or '.jpg'
        filename = datetime.now().strftime(f"avatar_{user_id}_%Y%m%d%H%M%S{file_ext}")
        
        profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data', 'profile_picture'))
        os.makedirs(profile_dir, exist_ok=True)
        
        file_path = os.path.join(profile_dir, filename)
        await bot.download_file(file.file_path, destination=file_path)
        
        logging.info(f"Аватар для пользователя {user_id} сохранен как {filename}")
        return filename
    except Exception as e:
        logging.error(f"Ошибка загрузки аватара для {user_id}: {e}")
        return None

#----------создание чата-------------
async def request_chat_creation(user_data: dict):
    """Отправляет запрос на создание чата в сервис amo_send."""
    url = f"{AMO_SEND_URL}/create"
    logging.info(f"Отправка запроса на создание чата: URL={url}, Данные={json.dumps(user_data, ensure_ascii=False)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=user_data) as response:
                response_data = await response.json()
                if response.status == 200 and 'amocrm_id' in response_data:
                    amocrm_id = response_data['amocrm_id']
                    logging.info(f"Ответ от amo_send: Чат успешно создан, amocrm_id={amocrm_id}")
                    return amocrm_id
                else:
                    logging.error(f"Ошибка от amo_send: Статус={response.status}, Ответ={response_data}")
                    return None
    except Exception as e:
        logging.critical(f"Не удалось подключиться к сервису amo_send: {e}")
        return None

#----------отправление сообщения---------------
async def send_message_to_amocrm(amocrm_id: str, tg_id: str, text: str):
    """Отправляет запрос на отправку сообщения в сервис amo_send."""
    url = f"{AMO_SEND_URL}/send"
    payload = {"amocrm_id": amocrm_id, "tg_id": tg_id, "text": text}
    
    logging.info(f"Отправка запроса на отправку сообщения: URL={url}, Данные={json.dumps(payload, ensure_ascii=False)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logging.info(f"Сообщение для amocrm_id={amocrm_id} успешно отправлено через amo_send.")
                    return True
                else:
                    response_data = await response.json()
                    logging.error(f"Ошибка от amo_send при отправке сообщения: Статус={response.status}, Ответ={response_data}")
                    return False
    except Exception as e:
        logging.critical(f"Не удалось подключиться к сервису amo_send (/send): {e}")
        return False

async def process_user_message(message: types.Message, welcome_text=None):
    user = message.from_user
    tg_id = str(user.id)
    
    logging.info(f"Получено сообщение от tg_id={tg_id}")
    check_user = find_user_by_tg_id(tg_id)
    
    if check_user is None:
        logging.info(f"Пользователь tg_id={tg_id} новый. Запуск процесса создания.")
        
        avatar_filename = await download_user_avatar(bot, user.id)
        final_avatar_url = f'{BASE_AVATAR_URL}/profile_picture/{avatar_filename}' if avatar_filename else None

        user_data_for_amo = {
            "tg_id": tg_id,
            "name": user.full_name or 'User',
            "username": user.username,
            "avatar": final_avatar_url,
            "welcome_text": welcome_text or message.text
        }
        
        # 2. Отправляем данные в amo_send для создания чата
        amocrm_id = await request_chat_creation(user_data_for_amo)

        if not amocrm_id:
            await message.reply('Произошла ошибка при создании чата. нет amocrm id.')
            return
        
        # 3. Сохраняем связку в локальной БД
        create_user(
            amocrm_id=amocrm_id,
            tg_id=tg_id,
            name=user.full_name or 'User',
            username=user.username,
            avatar=avatar_filename
        )
        logging.info(f"Успешно завершено: Пользователь tg_id={tg_id} создан и связан с amocrm_id={amocrm_id}")
    else:
        # Логика для существующего пользователя (отправка в amo_send/send)
        amocrm_id = check_user['amocrm_id']
        logging.info(f"Пользователь tg_id={tg_id} уже существует (amocrm_id={amocrm_id}). Отправка сообщения.")
        # Здесь будет вызов функции отправки сообщения в amo_send
        await send_message_to_amocrm(amocrm_id, tg_id, message.text)


@dp.message(Command('start'))
async def start_handler(message: types.Message):
    await process_user_message(message, welcome_text='Чат создан из команды /start.')

@dp.message()
async def message_handler(message: types.Message):
    await process_user_message(message)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.info("Запуск Telegram-бота...")
    asyncio.run(main())

