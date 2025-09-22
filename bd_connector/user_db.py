# bd_connector/user_db.py

import asyncio
from typing import Union, Optional, Dict
import aio_pika
import json
import os
import logging
from pathlib import Path
import fcntl  # Для блокировки файла при записи

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
USERS_FILE = Path("/Data/users.json")

# Инициализация JSON-файла, если не существует
if not USERS_FILE.exists():
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)
    logger.info("Создан новый файл users.json")

async def get_connection() -> aio_pika.RobustConnection:
    retries = 10
    delay = 5  # секунды
    for attempt in range(retries):
        logger.info(f"Попытка подключения к RabbitMQ (попытка {attempt + 1}/{retries})")
        try:
            conn = await aio_pika.connect_robust(RABBITMQ_URL)
            logger.info("Подключение к RabbitMQ успешно")
            return conn
        except Exception as e:
            logger.error(f"Ошибка подключения к RabbitMQ: {e}. Повтор через {delay} сек.")
            await asyncio.sleep(delay)
    raise Exception(f"Не удалось подключиться к RabbitMQ после {retries} попыток")

async def process_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        try:
            data = json.loads(message.body)
            logger.info(f"Получено сообщение: {data}")
            request_type = data.get("type")
            payload = data.get("payload", {})
            correlation_id = data.get("correlation_id")
            reply_to = data.get("reply_to")

            if request_type == "find_user":
                user = await find_user_by_tg_id(payload.get("tg_id"))
                response = {"result": user}
            elif request_type == "create_user":
                success = await create_user(**payload)
                response = {"result": {"success": success}}
            else:
                logger.warning(f"Неизвестный тип запроса: {request_type}")
                return

            # Отправка ответа
            connection = await get_connection()
            channel = await connection.channel()
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(response).encode(),
                    correlation_id=correlation_id,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=reply_to
            )
            await connection.close()
            logger.info(f"Отправлен ответ на {reply_to}: {response}")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

async def find_user_by_tg_id(tg_id: str) -> Union[Dict[str, str], None]:
    logger.info(f"Поиск пользователя по tg_id: {tg_id}")
    try:
        with open(USERS_FILE, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Блокировка на чтение
            users = json.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        user = users.get(tg_id)
        if user:
            logger.info(f"Пользователь найден: {user}")
            return user
        else:
            logger.info(f"Пользователь не найден: {tg_id}")
            return None
    except Exception as e:
        logger.error(f"Ошибка чтения users.json: {e}")
        return None

async def create_user(amocrm_id: str, tg_id: str, name: str, username: Optional[str], avatar: Optional[str]) -> bool:
    logger.info(f"Создание пользователя: tg_id={tg_id}, amocrm_id={amocrm_id}")
    try:
        with open(USERS_FILE, 'r+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Блокировка на запись
            users = json.load(f)
            users[tg_id] = {
                "amocrm_id": amocrm_id,
                "name": name,
                "username": username,
                "avatar": avatar
            }
            f.seek(0)
            json.dump(users, f, indent=4)
            f.truncate()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        logger.info(f"Пользователь успешно создан: {tg_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка создания пользователя: {e}")
        return False

async def main() -> None:
    try:
        connection = await get_connection()
        channel = await connection.channel()
        await channel.declare_queue("user_requests", durable=True)
        logger.info("Очередь RabbitMQ инициализирована")

        queue = await channel.declare_queue("user_requests", durable=True)
        await queue.consume(process_message, no_ack=False)
        logger.info("Потребитель RabbitMQ запущен. Ожидание сообщений...")

        await asyncio.Future()  # Держим в работе бесконечно
    except Exception as e:
        logger.critical(f"Критическая ошибка в main: {e}")

if __name__ == "__main__":
    asyncio.run(main())
