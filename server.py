from flask import Flask, request
import requests, json, sys, hashlib, hmac, time

# ---------- ВАШИ ДАННЫЕ ---------- #
SECRET      = '5qv05iXr2OxuxCUwfjkKr8L1NsFZlaZtsTihCN4iFltacoADNdOCxMrBt3tmbzYy'  # Секретный ключ AmoCRM
CHANNEL_ID  = '1f79e336-e5e9-4968-adb6-b6a103f54145'  # ID интеграции в AmoCRM
AMOJO_ID    = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjI3NjQ0NDVjNzczODhkYzg2ZDNmYTNmNDMyYjJlMzMxYmI3NzExMjFkYzM5ZDE0ZjBmYTRkNDI0ZWQ1ZWQxOTliYmQ2MmM2NzZhMmQ4YTQ0In0.eyJhdWQiOiIxZjc5ZTMzNi1lNWU5LTQ5NjgtYWRiNi1iNmExMDNmNTQxNDUiLCJqdGkiOiIyNzY0NDQ1Yzc3Mzg4ZGM4NmQzZmEzZjQzMmIyZTMzMWJiNzcxMTIxZGMzOWQxNGYwZmE0ZDQyNGVkNWVkMTk5YmJkNjJjNjc2YTJkOGE0NCIsImlhdCI6MTc1NjMyODAzNSwibmJmIjoxNzU2MzI4MDM1LCJleHAiOjE5MTQwMTkyMDAsInN1YiI6IjEyNTYxODk4IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyNDU0OTkwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwidXNlcl9mbGFncyI6MCwiaGFzaF91dWlkIjoiNWExN2YzYWMtMWY3Ny00M2Y5LWE3NDAtZWEyMDlkZjY5MWE4IiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.Ao2Koas0ZL03FUB76HVIQ5R3SI4HgS0rKuuMfP_u6wFv3dZ4q1NIQSrABVrzUgJimDZvERKDBubavg-pluduRH15nqWfBn4xAbbwu8rVHE2g5K32Bhnui0LlQUXXx86cktF7PhBXq6Kh6QJLF2_v6CCTbdy3e_7o5JFxltleKxYcy3m_ksDIdezASDTs-PZ4FoWTeG8HXqb1q4R6ORajV5iWCZVy88-RxdPptm0EFSvp1BgZ4A18Z16rhhMW1pKZjCLOwiZTpl3zlenWFqmLwSlp9mFEAsgTPafpRtiExZmDDrYkVMVsMPs0U5Sx2cqWGelLhJstP_eI1iADUH6cVQ'  # Долгосрочный AmoCRM (API /account?with=amojo_id)
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

