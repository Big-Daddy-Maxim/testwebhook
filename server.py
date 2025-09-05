from flask import Flask, request
import requests
import json
import sys
import hashlib
import hmac
import time
import os

# ---------- ДАННЫЕ ИЗ ВАШЕГО JSON ---------- #
SECRET = 'c4f35fc977d2fd1437bc72e1e50791bd3afbcc9f'  # secret_key из JSON
CHANNEL_ID = '69d64ccd-90e0-4566-bc0c-507d47f44b12'  # id из JSON
AMOJO_ID = 'd4216b47-0698-4c13-9b37-ead5cf5ff44c'  # id из allowed_acc_list

TELEGRAM_BOT_TOKEN = '8040130333:AAFG5W13u0E0mWlpAkjIkvOD3W1WnceDMBc'  # Токен TG-бота
CONVERSATIONS_FILE = 'conversations_map.json'  # Файл mapping (conv_id -> chat_id)

app = Flask(__name__)

# Загрузка mapping
def load_conversations() -> dict:
    if os.path.exists(CONVERSATIONS_FILE):
        with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {}

conversations_map = load_conversations()

# Проверка подписи webhook (для безопасности)
def verify_signature(secret, body, received_sig, date, path, method='POST', content_type='application/json'):
    body_str = json.dumps(body)
    md5 = hashlib.md5(body_str.encode()).hexdigest()
    to_sign = f"{method.upper()}\n{md5}\n{content_type}\n{date}\n{path}"
    calculated_sig = hmac.new(secret.encode(), to_sign.encode(), hashlib.sha1).hexdigest()
    return calculated_sig == received_sig

# ---------- МАРШРУТЫ ---------- #

@app.route('/', methods=['GET'])
def index():
    return 'Server running', 200

@app.route('/webhook/', methods=['GET', 'POST'])
@app.route('/webhook', defaults={'scope_id': ''}, methods=['GET', 'POST'])
def webhook(scope_id):
    if request.method == 'POST':
        data = request.get_json(silent=True)
        print(f'\n==> POST (scope_id = {scope_id})')
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # Проверка подписи
        received_sig = request.headers.get('X-Signature')
        date = request.headers.get('Date')
        path = f'/webhook/{scope_id}' if scope_id else '/webhook'
        if not verify_signature(SECRET, data, received_sig, date, path):
            print('Invalid signature!')
            return 'Invalid signature', 403

        if '_' in scope_id:
            ch_id, amo_id = scope_id.split('_', 1)
            print(f'Пункт 2 → Канал: {ch_id} | Аккаунт: {amo_id}')

        # Логика отправки в Telegram (если new_message от менеджера)
        if data and data.get('event_type') == 'new_message':
            payload = data.get('payload', {})
            conversation_id = payload.get('conversation_id')
            message_text = payload.get('message', {}).get('text')
            sender = payload.get('sender', {})

            # Проверяем, что сообщение от менеджера (не от клиента)
            if sender.get('id') != payload.get('user_id'):  # Предполагаем, что sender.id менеджера отличается
                if conversation_id and message_text:
                    chat_id = conversations_map.get(conversation_id)
                    if chat_id:
                        telegram_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
                        telegram_payload = {'chat_id': chat_id, 'text': f'От менеджера: {message_text}'}
                        response = requests.post(telegram_url, json=telegram_payload)
                        if response.status_code == 200:
                            print(f'Отправлено в TG: {message_text}')
                        else:
                            print(f'Ошибка TG: {response.text}')
                    else:
                        print(f'Нет chat_id для conv_id: {conversation_id}')

        return 'success', 200
    return f'GET success (scope_id = {CHANNEL_ID}_{AMOJO_ID})', 200

@app.route('/favicon.ico')
def favicon():
    return '', 204

# ---------- ПРИВЯЗКА КАНАЛА (пункт 8) ---------- #

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
        print(f'Пункт 8 → Канал привязан! scope_id = {scope_id}')
    else:
        print('Ошибка привязки канала:', r.status_code, r.text)

# ---------- ЗАПУСК ---------- #

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--bind':
        bind_channel()
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)

