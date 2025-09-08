from flask import Flask, request
import requests
import json
import sys
import hashlib
import hmac
import time
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация из .env
SECRET = os.environ.get('CHANNEL_SECRET')
CHANNEL_ID = os.environ.get('CHANNEL_ID')
AMOJO_ID = os.environ.get('AMOJO_ID')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data'))
CONVERSATIONS_FILE = os.path.join(DATA_DIR, 'conversations_map.json')

app = Flask(__name__)

# Обработчик ошибок 400
@app.errorhandler(400)
def handle_bad_request(e):
    logger.info(f"Обработана ошибка 400: {e} от {request.remote_addr}")
    return 'Bad Request (Invalid protocol or data)', 400

# Загрузка mapping
def load_conversations() -> dict:
    if os.path.exists(CONVERSATIONS_FILE):
        with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {}

# Проверка подписи webhook (с отладкой и фиксами)
def verify_signature(secret, body, received_sig, date, path, method='POST', content_type='application/json'):
    if received_sig is None:
        logger.warning("Ошибка: Отсутствует заголовок X-Signature")
        return False
    
    # Без сортировки ключей для совпадения с amoCRM
    body_str = json.dumps(body)
    md5 = hashlib.md5(body_str.encode('utf-8')).hexdigest().lower()
    
    # Используем входящий date, если есть
    if date is None:
        date = time.strftime('%a, %d %b %Y %H:%M:%S +0000', time.gmtime())
    
    str_to_sign = f"{method.upper()}\n{md5}\n{content_type}\n{date}\n{path}"
    calculated_sig = hmac.new(secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha1).hexdigest().lower()
    
    # Отладка
    logger.debug(f"received_sig={received_sig}, calculated_sig={calculated_sig}")
    logger.debug(f"str_to_sign={str_to_sign}")
    logger.debug(f"md5={md5}, date={date}, path={path}")
    
    return calculated_sig == received_sig.lower()

# Объединённый маршрут для webhook
@app.route('/webhook', defaults={'scope_id': ''}, methods=['GET', 'POST'])
@app.route('/webhook/<scope_id>', methods=['GET', 'POST'])
def webhook(scope_id):
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True)
            if data is None:
                raise ValueError("Invalid JSON")
        except Exception as e:
            logger.error(f"Ошибка парсинга JSON: {e} от {request.remote_addr}")
            return 'Invalid request', 400

        # Логирование входящих данных
        logger.info(f'POST (scope_id = {scope_id}) data: {json.dumps(data)}')

        # Проверка подписи (не нужно проверять подписи это ненужно)
        received_sig = request.headers.get('X-Signature')
        date = request.headers.get('Date')
        path = f'/webhook/{scope_id}' if scope_id else '/webhook'
        content_type = request.headers.get('Content-Type', 'application/json')
        sig_valid = verify_signature(SECRET, data, received_sig, date, path, content_type=content_type)


        # Парсинг структуры данных
        if 'message' in data:
            message_data = data['message']
            conversation_id = message_data['conversation']['client_id']  # 'conv-1757348573'
            tg_id = message_data['receiver']['client_id']  # '1226674712'
            message_text = message_data['message']['text']  # '555555555555555555'
            sender_id = message_data['sender']['id']

            # Проверка, что сообщение от менеджера (sender_id != tg_id)
            if message_text and conversation_id and tg_id and sender_id != tg_id:
                # Для дополнительной проверки можно использовать mapping, но tg_id уже в данных
                telegram_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
                telegram_payload = {'chat_id': tg_id, 'text': message_text}
                response = requests.post(telegram_url, json=telegram_payload)
                if response.status_code == 200:
                    logger.info(f'Отправлено в TG ({tg_id}): {message_text}')
                else:
                    logger.error(f'Ошибка отправки в TG: {response.text} - Status: {response.status_code}')
            else:
                logger.info("Сообщение не от менеджера или отсутствуют данные")

        return 'success', 200

    logger.info(f'GET success (scope_id = {scope_id or CHANNEL_ID + "_" + AMOJO_ID}) from IP: {request.remote_addr}')
    return f'GET success (scope_id = {scope_id or CHANNEL_ID + "_" + AMOJO_ID})', 200

@app.route('/favicon.ico')
def favicon():
    return '', 204

# Привязка канала
def bind_channel():
    path = f'/v2/origin/custom/{CHANNEL_ID}/connect'
    url = f'https://amojo.amocrm.ru{path}'
    body = {'account_id': AMOJO_ID,
            'title': 'MyWebhook',
            'hook_api_version': 'v2'}
    body_str = json.dumps(body)
    md5 = hashlib.md5(body_str.encode()).hexdigest()
    date = time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime())
    to_sign = f"POST\n{md5}\napplication/json\n{date}\n{path}"
    sig = hmac.new(SECRET.encode(), to_sign.encode(), hashlib.sha1).hexdigest()
    r = requests.post(
        url, data=body_str,
        headers={'Content-Type': 'application/json',
                 'Content-MD5': md5,
                 'Date': date,
                 'X-Signature': sig})
    if r.status_code == 200:
        scope_id = r.json().get('scope_id')
        logger.info(f'Канал привязан! scope_id = {scope_id}')
    else:
        logger.error(f'Ошибка привязки канала: {r.status_code} {r.text}')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--bind':
        bind_channel()
    else:
        app.run(host='0.0.0.0', port=80, debug=False)
