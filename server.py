from flask import Flask, request
import requests
import json
import sys
import hashlib
import hmac
import time

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return 'Server running', 200


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(data)  # Выводим полученные данные (здесь будет scope_id после настройки)
    # Пример разбора scope_id: if 'scope_id' in data: parts = data['scope_id'].split('_'); channel_id, amojo_id = parts[0], parts[1]
    return 'success', 200


@app.route('/favicon.ico')
def favicon():
    return '', 204


def get_amojo_id():
    """Шаг 1: Получаем amojo_id аккаунта через API AmoCRM."""
    access_token = 'ВАШ_ACCESS_TOKEN'  # Замените на реальный access_token (см. объяснение ниже)
    base_url = 'https://ВАШ_ПОДДОМЕН.amocrm.ru'  # Замените на ваш поддомен (e.g., https://mycompany.amocrm.ru)

    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'{base_url}/api/v4/account?with=amojo_id', headers=headers)

    if response.status_code == 200:
        data = response.json()
        amojo_id = data.get('amojo_id')
        print('Amojo ID:', amojo_id)
        return amojo_id
    else:
        print('Ошибка:', response.status_code, response.text)
        return None


def get_scope_id():
    """Шаг 2: Подключаем канал и получаем scope_id."""
    secret = 'ВАШ_SECRET_KEY'  # Замените на secret из настроек канала (см. объяснение ниже)
    channel_id = 'ВАШ_CHANNEL_ID'  # Замените на ID вашего канала (см. объяснение ниже)
    amojo_id = 'ВАШ_AMOJO_ID'  # Замените на значение из get_amojo_id() (или запустите --get-amojo сначала)

    path = f'/v2/origin/custom/{channel_id}/connect'
    url = f'https://amojo.amocrm.ru{path}'

    body = {
        'account_id': amojo_id,
        'title': 'MyWebhookChannel',  # Можно изменить на название вашего канала
        'hook_api_version': 'v2'  # Рекомендуемая версия
    }
    request_body = json.dumps(body)
    content_md5 = hashlib.md5(request_body.encode()).hexdigest()
    date = time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime())
    method = 'POST'
    content_type = 'application/json'

    str_to_sign = f"{method.upper()}\n{content_md5}\n{content_type}\n{date}\n{path}"
    signature = hmac.new(secret.encode(), str_to_sign.encode(), hashlib.sha1).hexdigest()

    headers = {
        'Content-Type': content_type,
        'Content-MD5': content_md5,
        'Date': date,
        'X-Signature': signature
    }

    response = requests.post(url, data=request_body, headers=headers)
    if response.status_code == 200:
        data = response.json()
        scope_id = data.get('scope_id')
        print('Scope ID:', scope_id)
        return scope_id
    else:
        print('Ошибка:', response.status_code, response.text)
        return None


def test_webhook():
    """Тестовый POST-запрос на ваш webhook (как в оригинале)."""
    webhook_url = 'http://83.166.235.207/webhook'
    data = {
        'name': 'MyWebhook',
        'Channel URL': 'test url'
    }
    headers = {'Content-Type': 'application/json'}
    try:
        r = requests.post(webhook_url, data=json.dumps(data), headers=headers)
        print('Status code:', r.status_code)
        print('Response:', r.text)
        if r.status_code == 200:
            print('Подтверждение отправлено успешно!')
        else:
            print('Ошибка при отправке подтверждения.')
    except Exception as e:
        print('Ошибка подключения:', str(e))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == '--test':
            test_webhook()
        elif mode == '--get-amojo':
            get_amojo_id()
        elif mode == '--get-scope':
            get_scope_id()
        else:
            print('Неизвестный режим. Доступно: --test, --get-amojo, --get-scope')
            sys.exit(1)
    else:
        app.run(host='0.0.0.0', port=80)  # Запуск сервера по умолчанию
