from __future__ import annotations

import json
import hashlib
import hmac
import requests
from datetime import datetime
import time
import os
from dotenv import load_dotenv
import logging
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()  # Загружаем .env

# Конфигурация из .env
channel_secret = os.environ.get('CHANNEL_SECRET')
scope_id = os.environ.get('SCOPE_ID')
base_url = os.environ.get('BASE_URL', 'https://amojo.amocrm.ru')

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data'))
USER_FILE = os.path.join(DATA_DIR, 'user_conversations.json')

def load_users() -> List[Dict]:
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                data = json.loads(content)
                # Миграция: если старый формат (dict), преобразуем в список
                if isinstance(data, dict):
                    new_data = []
                    for tg_id, amocrm_id in data.items():
                        new_data.append({
                            'amocrm_id': amocrm_id,
                            'tg_id': tg_id,
                            'name': 'User',
                            'username': None,
                            'email': 'default@example.com',
                            'phone': '+79999999999',
                            'avatar': 'https://example.com/avatar.png'
                        })
                    # Сохраняем мигрированные данные
                    save_users(new_data)
                    return new_data
                elif isinstance(data, list):
                    return data
    return []

def save_users(data: List[Dict]) -> None:
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

user_conversations: List[Dict] = load_users()

# Вспомогательные функции amoCRM
def create_body_checksum(body: str) -> str:
    return hashlib.md5(body.encode('utf-8')).hexdigest().lower()

def create_signature(secret: str, checksum: str, api_method: str, http_method: str = 'POST', content_type: str = 'application/json') -> str:
    date_rfc = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    str_to_sign = '\n'.join([http_method.upper(), checksum, content_type, date_rfc, api_method])
    return hmac.new(secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha1).hexdigest().lower()

def prepare_headers(checksum: str, signature: str, content_type: str = 'application/json') -> Dict[str, str]:
    date_rfc = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    return {
        'Date': date_rfc,
        'Content-Type': content_type,
        'Content-MD5': checksum,
        'X-Signature': signature,
        'User-Agent': 'FlowSync-Integration/1.0'
    }

# Поиск или создание чата по tg_id
async def create_chat_amo(
    tg_id: str,
    name: str = 'User',
    username: Optional[str] = None,
    email: str = 'default@example.com',
    phone: str = '+79999999999',
    avatar: str = 'https://example.com/avatar.png',
    welcome_text: str = 'Привет! Чат создан.'
) -> Optional[str]:
    # Создание нового чата в amoCRM
    amocrm_id = f'conv-{int(time.time())}'
    request_body = {
        'event_type': 'new_message',
        'payload': {
            'timestamp': int(time.time()),
            'msec_timestamp': int(time.time() * 1000),
            'msgid': f'msg-{int(time.time())}',
            'conversation_id': amocrm_id,
            'sender': {
                'id': tg_id,
                'avatar': avatar,
                'profile': {
                    'phone': phone,
                    'email': email
                },
                'name': name
            },
            'message': {
                'type': 'text',
                'text': welcome_text,
            },
            'silent': False
        }
    }
    json_body = json.dumps(request_body)
    logging.info(f"Создано тело запроса: {json_body}")
    api_method = f'/v2/origin/custom/{scope_id}'
    checksum = create_body_checksum(json_body)
    signature = create_signature(channel_secret, checksum, api_method)
    headers = prepare_headers(checksum, signature)
    logging.info(f"Созданы заголовки: {headers}")
    url = base_url + api_method
    # Логирование перед POST
    logging.info(f"Отправка POST на {url} с телом: {json_body}")
    response = requests.post(url, data=json_body, headers=headers)
    logging.info(f"Ответ от amoCRM (create chat): статус {response.status_code}, тело: {response.text}")
    if response.status_code == 200:
        return amocrm_id
    else:
        logging.error(f"Ошибка создания чата: {response.status_code} {response.text}")
        return None

# Отправка сообщения в amoCRM
async def send_message_to_amocrm(amocrm_id: str, tg_id: str, text: str) -> bool:
    request_body = {
        'event_type': 'new_message',
        'payload': {
            'timestamp': int(time.time()),
            'msec_timestamp': int(time.time() * 1000),
            'msgid': f'msg-{int(time.time())}',
            'conversation_id': amocrm_id,
            'sender': {
                'id': tg_id
            },
            'message': {
                'type': 'text',
                'text': text
            },
            'silent': False
        }
    }
    json_body = json.dumps(request_body)
    api_method = f'/v2/origin/custom/{scope_id}'
    checksum = create_body_checksum(json_body)
    signature = create_signature(channel_secret, checksum, api_method)
    headers = prepare_headers(checksum, signature)
    url = base_url + api_method
    # Логирование перед POST
    logging.info(f"Отправка POST на {url} с телом: {json_body}")
    response = requests.post(url, data=json_body, headers=headers)
    logging.info(f"Ответ от amoCRM (send message): статус {response.status_code}, тело: {response.text}")
    return response.status_code == 200

# Pydantic модели для запросов
class CreateChatRequest(BaseModel):
    tg_id: str
    name: str = 'User'
    username: str = None
    email: str = 'default@example.com'
    phone: str = '+79999999999'
    avatar: str = 'https://example.com/avatar.png'
    welcome_text: str = 'Привет! Чат создан.'

class SendMessageRequest(BaseModel):
    amocrm_id: str
    tg_id: str
    text: str

# FastAPI приложение
app = FastAPI()

@app.post("/create")
async def api_create_chat(request: CreateChatRequest = Body(...)):
    logging.info(f"Запрос на создание чата для tg_id: {request.tg_id}")
    amocrm_id = await create_chat_amo(
        request.tg_id, request.name, request.username, request.email, request.phone, request.avatar, request.welcome_text
    )
    if amocrm_id:
        logging.info(f"Чат успешно создан: {amocrm_id}")
        return {"amocrm_id": amocrm_id}
    else:
        logging.error("Не удалось создать чат")
        raise HTTPException(status_code=500, detail="Failed to create chat")

@app.post("/send")
async def api_send_message(request: SendMessageRequest = Body(...)):
    logging.info(f"Запрос на отправку сообщения в чат {request.amocrm_id} от tg_id: {request.tg_id}")
    success = await send_message_to_amocrm(request.amocrm_id, request.tg_id, request.text)
    if success:
        logging.info("Сообщение успешно отправлено")
        return {"status": "Message sent successfully"}
    else:
        logging.error("Не удалось отправить сообщение")
        raise HTTPException(status_code=500, detail="Failed to send message")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80) 
