from flask import Flask, request
import requests, json, sys, hashlib, hmac, time

# ---------- ВАШИ ДАННЫЕ ---------- #
SECRET      = 'Y3VUaXN7Shga5rbXO6lZRGhvKcBG4BhTQinEERh932BbbPOSZ8pHBAhI0qn2b2uG'  # Секретный ключ AmoCRM
CHANNEL_ID  = '1f79e336-e5e9-4968-adb6-b6a103f54145'  # ID интеграции в AmoCRM
AMOJO_ID    = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjM1Y2E2NTUxOTViY2Q5MDUyNmYxNDk5OTRjZWYzMzdmZDQxODUxNDkzMmYyZDQwMWJmNWMyZTYxYzlmNzRhYzI0MmZiMmQzOWQzMzc5MjJkIn0.eyJhdWQiOiIxZjc5ZTMzNi1lNWU5LTQ5NjgtYWRiNi1iNmExMDNmNTQxNDUiLCJqdGkiOiIzNWNhNjU1MTk1YmNkOTA1MjZmMTQ5OTk0Y2VmMzM3ZmQ0MTg1MTQ5MzJmMmQ0MDFiZjVjMmU2MWM5Zjc0YWMyNDJmYjJkMzlkMzM3OTIyZCIsImlhdCI6MTc1NjMyNDkyOSwibmJmIjoxNzU2MzI0OTI5LCJleHAiOjE5MTQwMTkyMDAsInN1YiI6IjEyNTYxODk4IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyNDU0OTkwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwidXNlcl9mbGFncyI6MCwiaGFzaF91dWlkIjoiMDA3YTkxMGQtYzQ5Zi00MjFkLWE4YTUtYWY2M2Q4ZmY3YmQzIiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.atkN4IrSMuw_HocIQPicl_DQ_td-4gEMKFbRF_Su_Lg8Cdw6J3pdV-ZRS-QTB3SV7eVxJbqQHV9Hhi3zAWU3k8kO3BVtxabPDgAFKuhnKXw7MxicgHLPeJtandIwp5mzrMg9-s4ULP-KIwioPexNIVXzmlB6JE8e6fNT5iw7xEqP8M3LT8vdzic0YrvBeAZ_8Suu7wvdsMwhnApX26Safl9Dmx59MCodpG58cQK1G_O_bFIeLRl6PMc3_Ay08HwgiPJhZn5cxzd3L0V_En_5fTYqPftQ6xADBv4b-nIw831dyGAz6fzZY8HZ5XiIQVVC_GCW6MiiEmcepjp7SmuEyQ'  # Долгосрочный AmoCRM (API /account?with=amojo_id)
# ---------------------------------- #

app = Flask(__name__)

# Печатаем подсказки сразу после запуска
print(f'Пункт 2 → scope_id формируется так: {CHANNEL_ID}_{AMOJO_ID}')
print('Пункт 8 → если канал не привязан, запустите:  python3 server.py --bind\n')

# ---------- FLASK ---------- #
@app.route('/', methods=['GET'])
def index():
    return 'Server running', 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        data = request.get_json()
        print('Данные от AmoCRM:', json.dumps(data, ensure_ascii=False, indent=2))

        if 'scope_id' in data:
            channel_id, amojo_id = data['scope_id'].split('_', 1)
            print(f'Пункт 2 → Канал: {channel_id} | Аккаунт: {amojo_id}')
        return 'success', 200
    return 'GET success', 200

@app.route('/favicon.ico')
def favicon():
    return '', 204

# ---------- ПРИВЯЗКА КАНАЛА (пункт 8) ---------- #
def bind_channel_and_get_scope():
    """Привязываем канал к интеграции и получаем scope_id."""
    path = f'/v2/origin/custom/{CHANNEL_ID}/connect'
    url  = f'https://amojo.amocrm.ru{path}'

    body = {
        'account_id': AMOJO_ID,
        'title': 'MyWebhook',
        'hook_api_version': 'v2'
    }
    body_str   = json.dumps(body)
    content_md5 = hashlib.md5(body_str.encode()).hexdigest()
    date        = time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime())
    string2sign = f"POST\n{content_md5}\napplication/json\n{date}\n{path}"
    signature   = hmac.new(SECRET.encode(), string2sign.encode(), hashlib.sha1).hexdigest()
    headers = {
        'Content-Type': 'application/json',
        'Content-MD5':  content_md5,
        'Date':         date,
        'X-Signature':  signature
    }

    r = requests.post(url, data=body_str, headers=headers)
    if r.status_code == 200:
        scope_id = r.json().get('scope_id')
        print(f'Пункт 8 → Канал привязан! scope_id = {scope_id}')
        return scope_id
    print('Ошибка привязки канала:', r.status_code, r.text)
    return None

# ---------- ЗАПУСК ---------- #
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--bind':
        bind_channel_and_get_scope()
    else:
        app.run(host='0.0.0.0', port=80, debug=True)

