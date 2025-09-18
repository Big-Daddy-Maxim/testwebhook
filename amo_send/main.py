# amo_send/main.py

from __future__ import annotations

import json
import hashlib
import hmac
import requests
import time
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

# --- 1. НАСТРОЙКА ЛОГГЕРА ---
# Настраиваем логирование для вывода сообщений в stdout, что удобно для Docker
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | [%(filename)s:%(lineno)d] | %(message)s',
    handlers=[logging.StreamHandler()]
)

# --- 2. ЗАГРУЗКА КОНФИГУРАЦИИ ---
load_dotenv()

channel_secret = os.environ.get('CHANNEL_SECRET')
scope_id = os.environ.get('SCOPE_ID')
base_url = os.environ.get('BASE_URL', 'https://amojo.amocrm.ru')

# --- 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ AMO CRM API ---

def create_body_checksum(body: str) -> str:
    """Создает MD5-чексумму тела запроса."""
    return hashlib.md5(body.encode('utf-8')).hexdigest().lower()

def create_signature(secret: str, checksum: str, api_method: str, http_method: str = 'POST', content_type: str = 'application/json') -> str:
    """Создает HMAC-SHA1 подпись для заголовка X-Signature."""
    date_rfc = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    str_to_sign = '\n'.join([http_method.upper(), checksum, content_type, date_rfc, api_method])
    
    signature = hmac.new(secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha1).hexdigest().lower()
   
    clean_str_to_sign = str_to_sign.replace('\n', ' ')
    logging.info(f"Сгенерирована подпись: {signature} для строки: '{clean_str_to_sign}'")

    return signature

def prepare_headers(checksum: str, signature: str) -> Dict[str, str]:
    """Готовит словарь с заголовками для запроса к amoCRM."""
    date_rfc = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    headers = {
        'Date': date_rfc,
        'Content-Type': 'application/json',
        'Content-MD5': checksum,
        'X-Signature': signature,
        'User-Agent': 'FlowSync-Integration/1.0'
    }
    return headers

#-------отправления сообщния для существующего пользователя--------
async def send_message_to_amo(amocrm_id: str, tg_id: str, text: str) -> bool:
    """Отправляет сообщение в существующий чат amoCRM."""
    logging.info(f"Начало отправки сообщения в чат amocrm_id={amocrm_id}")
    request_body = {
        "event_type": "new_message",
        "payload": {
            "timestamp": int(time.time()),
            "msgid": f"msg-{int(time.time())}",
            "conversation_id": amocrm_id,
            "sender": {"id": str(tg_id)},
            "message": {"type": "text", "text": text},
        }
    }
    json_body = json.dumps(request_body, ensure_ascii=False)
    api_method = f'/v2/origin/custom/{scope_id}'
    checksum = create_body_checksum(json_body)
    signature = create_signature(channel_secret, checksum, api_method)
    headers = prepare_headers(checksum, signature)
    url = base_url + api_method
    
    logging.info(f"Отправка запроса в amoCRM (send): URL={url}, Body={json_body}")
    try:
        response = requests.post(url, data=json_body.encode('utf-8'), headers=headers, timeout=10)
        logging.info(f"Ответ от amoCRM (send): Статус={response.status_code}, Тело={response.text or 'пусто'}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.critical(f"Сетевая ошибка при отправке сообщения в amoCRM: {e}")
        return False


# --- 4. ОСНОВНАЯ ЛОГИКА ВЗАИМОДЕЙСТВИЯ С AMO CRM ---

async def create_chat_amo(
    tg_id: str, name: str, username: Optional[str], avatar: Optional[str], welcome_text: str
) -> Optional[str]:
    """
    Формирует и отправляет запрос в amoCRM для создания нового чата.
    Возвращает amocrm_id в случае успеха, иначе None.
    """
    logging.info(f"Начало создания чата в amoCRM для tg_id={tg_id}")
    
    amocrm_id = f'conv-{int(time.time())}'
    
    request_body = {
        "event_type": "new_message",
        "payload": {
            "timestamp": int(time.time()),
            "msgid": f"msg-{int(time.time())}",
            "conversation_id": amocrm_id,
            "sender": {
                "id": str(tg_id),
                "name": name,
                "username": username,
                "avatar": avatar,
                "profile": {} # Можно добавить phone, email, если они есть
            },
            "message": {"type": "text", "text": welcome_text},
            "silent": False
        }
    }
    json_body = json.dumps(request_body, ensure_ascii=False)
    
    api_method = f'/v2/origin/custom/{scope_id}'
    checksum = create_body_checksum(json_body)
    signature = create_signature(channel_secret, checksum, api_method)
    headers = prepare_headers(checksum, signature)
    url = base_url + api_method
    
    logging.info(f"Отправка запроса в amoCRM: URL={url}, Headers={json.dumps(headers)}, Body={json_body}")
    
    try:
        response = requests.post(url, data=json_body.encode('utf-8'), headers=headers, timeout=15)
        
        logging.info(f"Получен ответ от amoCRM: Статус={response.status_code}, Тело={response.text or 'пусто'}")
        
        if response.status_code == 200:
            logging.info(f"УСПЕХ: Чат в amoCRM успешно создан. amocrm_id={amocrm_id}")
            return amocrm_id
        else:
            logging.error(f"ОШИБКА: amoCRM вернул ошибку при создании чата. Статус: {response.status_code}, Тело: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logging.critical(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось подключиться к API amoCRM. Ошибка: {e}")
        return None

# --- 5. PYDANTIC МОДЕЛИ ДЛЯ ВАЛИДАЦИИ ЗАПРОСОВ ---

class CreateChatRequest(BaseModel):
    tg_id: str
    name: str = 'User'
    username: Optional[str] = None
    avatar: Optional[str] = None
    welcome_text: str = 'Чат создан.'

class SendMessageRequest(BaseModel):
    amocrm_id: str
    tg_id: str
    text: str

# --- 6. FASTAPI ПРИЛОЖЕНИЕ ---

app = FastAPI(
    title="AmoCRM Send Service",
    description="Микросервис для отправки данных в amoCRM.",
    version="1.2.0"
)

@app.post("/create", summary="Создать новый чат в amoCRM")
async def api_create_chat(request: CreateChatRequest = Body(...)):
    """
    Принимает данные нового пользователя от telegram_bot,
    создает чат в amoCRM и возвращает amocrm_id.
    """
    # model_dump_json удобен для логирования Pydantic-моделей
    logging.info(f"Получен входящий запрос на /create: {request.model_dump_json(indent=2)}")
    
    amocrm_id = await create_chat_amo(
        tg_id=request.tg_id,
        name=request.name,
        username=request.username,
        avatar=request.avatar,
        welcome_text=request.welcome_text
    )

    if amocrm_id:
        logging.info(f"Операция /create завершена успешно. Возвращаем amocrm_id: {amocrm_id}")
        return {"amocrm_id": amocrm_id, "status": "success"}
    else:
        logging.error("Операция /create не удалась. Не удалось создать чат в amoCRM.")
        raise HTTPException(
            status_code=500, 
            detail="Failed to create chat in amoCRM. See service logs for details."
        )

@app.post("/send", summary="Отправить сообщение")
async def api_send_message(request: SendMessageRequest = Body(...)):
    logging.info(f"Получен входящий запрос на /send: {request.model_dump_json(indent=2)}")
    success = await send_message_to_amo(
        amocrm_id=request.amocrm_id,
        tg_id=request.tg_id,
        text=request.text
    )
    if success:
        return {"status": "success", "message": "Message sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send message to amoCRM.")


@app.get("/health", summary="Проверка состояния сервиса")
def health_check():
    """Простой эндпоинт для проверки, что сервис запущен и работает."""
    logging.info("Проверка состояния /health выполнена успешно.")
    return {"status": "ok"}


# --- 7. ТОЧКА ВХОДА ДЛЯ ЗАПУСКА СЕРВЕРА ---

if __name__ == "__main__":
    logging.info("Запуск FastAPI-сервиса amo_send...")
    import uvicorn
    # ВАЖНО: порт 8000 указан, чтобы соответствовать настройкам в docker-compose.yml
    uvicorn.run(app, host="0.0.0.0", port=8000)
