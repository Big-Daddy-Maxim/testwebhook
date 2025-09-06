import asyncio
import json
import os
from dotenv import load_dotenv
from amo_crm_chat import (
    create_chat_from_telegram,
    send_message_to_amocrm,
    user_conversations,
)

FILE = "user_conversations.json"  

def load_map() -> dict:
    """Загружает ранее сохранённый словарь из FILE."""
    if os.path.exists(FILE):
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                data = f.read().strip()
                return json.loads(data) if data else {}
        except json.JSONDecodeError:
            return {}
    return {}

def save_map() -> None:
    """Сохраняет актуальный user_conversations в FILE."""
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(user_conversations, f, ensure_ascii=False, indent=4)

# Загружаем существующие связи TG ID → conversation_id
user_conversations.update(load_map())

async def test_main():
    """Тестовое создание чата и отправка сообщения без Telegram-бота."""
    uid = "conv-111111"  
    if uid not in user_conversations:
        conv_id = await create_chat_from_telegram(
            uid, "Test", "testuser", "test@mail"
        )
        if conv_id:
            print(f"Chat created: {conv_id}")
    success = await send_message_to_amocrm(
        user_conversations.get(uid), uid, "тест"
    )
    print("Send message:", "Success" if success else "Failed")
    save_map()

if __name__ == "__main__":
    asyncio.run(test_main())
