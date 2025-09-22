# bd_connector/main.py

import asyncio
import logging
from user_db import main as user_db_main  # Импорт main из user_db.py

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Запуск bd_connector...")
    asyncio.run(user_db_main())
