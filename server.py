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
    secret = 'Y3VUaXN7Shga5rbXO6lZRGhvKcBG4BhTQinEERh932BbbPOSZ8pHBAhI0qn2b2uG'  # Секретный ключ AmoCRM
    channel_id = '1f79e336-e5e9-4968-adb6-b6a103f54145'  # ID интеграции в AmoCRM
    amojo_id = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjM1Y2E2NTUxOTViY2Q5MDUyNmYxNDk5OTRjZWYzMzdmZDQxODUxNDkzMmYyZDQwMWJmNWMyZTYxYzlmNzRhYzI0MmZiMmQzOWQzMzc5MjJkIn0.eyJhdWQiOiIxZjc5ZTMzNi1lNWU5LTQ5NjgtYWRiNi1iNmExMDNmNTQxNDUiLCJqdGkiOiIzNWNhNjU1MTk1YmNkOTA1MjZmMTQ5OTk0Y2VmMzM3ZmQ0MTg1MTQ5MzJmMmQ0MDFiZjVjMmU2MWM5Zjc0YWMyNDJmYjJkMzlkMzM3OTIyZCIsImlhdCI6MTc1NjMyNDkyOSwibmJmIjoxNzU2MzI0OTI5LCJleHAiOjE5MTQwMTkyMDAsInN1YiI6IjEyNTYxODk4IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyNDU0OTkwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwidXNlcl9mbGFncyI6MCwiaGFzaF91dWlkIjoiMDA3YTkxMGQtYzQ5Zi00MjFkLWE4YTUtYWY2M2Q4ZmY3YmQzIiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.atkN4IrSMuw_HocIQPicl_DQ_td-4gEMKFbRF_Su_Lg8Cdw6J3pdV-ZRS-QTB3SV7eVxJbqQHV9Hhi3zAWU3k8kO3BVtxabPDgAFKuhnKXw7MxicgHLPeJtandIwp5mzrMg9-s4ULP-KIwioPexNIVXzmlB6JE8e6fNT5iw7xEqP8M3LT8vdzic0YrvBeAZ_8Suu7wvdsMwhnApX26Safl9Dmx59MCodpG58cQK1G_O_bFIeLRl6PMc3_Ay08HwgiPJhZn5cxzd3L0V_En_5fTYqPftQ6xADBv4b-nIw831dyGAz6fzZY8HZ5XiIQVVC_GCW6MiiEmcepjp7SmuEyQ'  # Долгосрочный AmoCRM (API /account?with=amojo_id)
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
