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

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        data = request.get_json()
        print('Данные от AmoCRM:', data)  # Выводит всё, что пришло (включая scope_id)
        # Пример разбора: if 'scope_id' in data: print('Scope ID:', data['scope_id'])
        return 'success', 200
    elif request.method == 'GET':
        return 'GET success', 200

@app.route('/favicon.ico')
def favicon():
    return '', 204

def get_scope_id():
    secret = 'ВАШ_SECRET_KEY'  # Из настроек канала в AmoCRM
    channel_id = 'ВАШ_CHANNEL_ID'  # ID вашего канала в AmoCRM
    amojo_id = 'ВАШ_AMOJO_ID'  # Получите из AmoCRM (API /account?with=amojo_id)
    path = f'/v2/origin/custom/{channel_id}/connect'
    url = f'https://amojo.amocrm.ru{path}'

    body = {
        'account_id': amojo_id,
        'title': 'MyWebhook',
        'hook_api_version': 'v2'
    }
    request_body = json.dumps(body)
    content_md5 = hashlib.md5(request_body.encode()).hexdigest()
    date = time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime())
    method = 'POST'
    content_type = 'application/json'

    str_to_sign = f"{method}\n{content_md5}\n{content_type}\n{date}\n{path}"
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
        print('Ваш scope_id:', scope_id)
        return scope_id
    else:
        print('Ошибка:', response.text)
        return None

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--get-scope':
        get_scope_id()
    else:
        app.run(host='0.0.0.0', port=80, debug=True)
