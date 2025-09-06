from __future__ import annotations
import json
import hashlib
import hmac
import requests
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Конфигурация (замените на реальные)
channel_secret = os.environ.get('CHANNEL_SECRET')
scope_id = os.environ.get('SCOPE_ID')
base_url = os.environ.get('BASE_URL', 'https://amojo.amocrm.ru')

USER_FILE = 'user_conversations.json'  # {tg_user_id: conv_id}

user_conversations = {}

def load_users() -> dict:
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {}

def save_users(data: dict) -> None:
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)

user_conversations.update(load_users())

# Вспомогательные функции amoCRM
def create_body_checksum(body: str) -> str:
    return hashlib.md5(body.encode('utf-8')).hexdigest().lower()

def create_signature(secret: str, checksum: str, api_method: str, http_method: str = 'POST', content_type: str = 'application/json') -> str:
    date_rfc = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    str_to_sign = '\n'.join([http_method.upper(), checksum, content_type, date_rfc, api_method])
    return hmac.new(secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha1).hexdigest().lower()

def prepare_headers(checksum: str, signature: str, content_type: str = 'application/json') -> dict:
    date_rfc = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    return {
        'Date': date_rfc,
        'Content-Type': content_type,
        'Content-MD5': checksum,
        'X-Signature': signature,
        'User-Agent': 'FlowSync-Integration/1.0'
    }

# Создание чата в amoCRM
async def create_chat_from_telegram(
    user_id: str,
    name: str = 'User',
    username: str | None = None,
    email: str = 'default@example.com',
    phone: str = '+79999999999',
    avatar: str = 'https://example.com/avatar.png',
    welcome_text: str = 'Привет! Чат создан.'
) -> str | None:
    conversation_id = f'conv-{int(time.time())}'
    request_body = {
        'event_type': 'new_message',
        'payload': {
            'timestamp': int(time.time()),
            'msec_timestamp': int(time.time() * 1000),
            'msgid': f'msg-{int(time.time())}',
            'conversation_id': conversation_id,
            'sender': {
                'id': user_id,
                'avatar': avatar,
                'profile': {
                    'phone': phone,
                    'email': email
                },
                'name': name
            },
            'message': {
                'type': 'text',
                'text': welcome_text
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
    response = requests.post(url, data=json_body, headers=headers)
    if response.status_code == 200:
        user_conversations[user_id] = conversation_id
        save_users(user_conversations)
        return conversation_id
    else:
        print(f"Ошибка создания чата: {response.status_code} {response.text}")
        return None

# Отправка сообщения в amoCRM
async def send_message_to_amocrm(conversation_id: str, user_id: str, text: str) -> bool:
    request_body = {
        'event_type': 'new_message',
        'payload': {
            'timestamp': int(time.time()),
            'msec_timestamp': int(time.time() * 1000),
            'msgid': f'msg-{int(time.time())}',
            'conversation_id': conversation_id,
            'sender': {
                'id': user_id
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
    response = requests.post(url, data=json_body, headers=headers)
    return response.status_code == 200
