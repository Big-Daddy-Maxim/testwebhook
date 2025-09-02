from flask import Flask, request, abort
import hmac
import hashlib
import json
import requests
import time
import sys

app = Flask(__name__)

# ---------- ВАШИ ДАННЫЕ ---------- #
SECRET      = '5qv05iXr2OxuxCUwfjkKr8L1NsFZlaZtsTihCN4iFltacoADNdOCxMrBt3tmbzYy'  # Секретный ключ AmoCRM
CHANNEL_ID  = '1f79e336-e5e9-4968-adb6-b6a103f54145'  # ID интеграции в AmoCRM
AMOJO_ID    = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjI3NjQ0NDVjNzczODhkYzg2ZDNmYTNmNDMyYjJlMzMxYmI3NzExMjFkYzM5ZDE0ZjBmYTRkNDI0ZWQ1ZWQxOTliYmQ2MmM2NzZhMmQ4YTQ0In0.eyJhdWQiOiIxZjc5ZTMzNi1lNWU5LTQ5NjgtYWRiNi1iNmExMDNmNTQxNDUiLCJqdGkiOiIyNzY0NDQ1Yzc3Mzg4ZGM4NmQzZmEzZjQzMmIyZTMzMWJiNzcxMTIxZGMzOWQxNGYwZmE0ZDQyNGVkNWVkMTk5YmJkNjJjNjc2YTJkOGE0NCIsImlhdCI6MTc1NjMyODAzNSwibmJmIjoxNzU2MzI4MDM1LCJleHAiOjE5MTQwMTkyMDAsInN1YiI6IjEyNTYxODk4IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyNDU0OTkwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwidXNlcl9mbGFncyI6MCwiaGFzaF91dWlkIjoiNWExN2YzYWMtMWY3Ny00M2Y5LWE3NDAtZWEyMDlkZjY5MWE4IiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.Ao2Koas0ZL03FUB76HVIQ5R3SI4HgS0rKuuMfP_u6wFv3dZ4q1NIQSrABVrzUgJimDZvERKDBubavg-pluduRH15nqWfBn4xAbbwu8rVHE2g5K32Bhnui0LlQUXXx86cktF7PhBXq6Kh6QJLF2_v6CCTbdy3e_7o5JFxltleKxYcy3m_ksDIdezASDTs-PZ4FoWTeG8HXqb1q4R6ORajV5iWCZVy88-RxdPptm0EFSvp1BgZ4A18Z16rhhMW1pKZjCLOwiZTpl3zlenWFqmLwSlp9mFEAsgTPafpRtiExZmDDrYkVMVsMPs0U5Sx2cqWGelLhJstP_eI1iADUH6cVQ'  # Долгосрочный AmoCRM (API /account?with=amojo_id)
# ---------------------------------- #

def save_text_message(receiver_id, chat_id, text):
    print(f"Save text message: Receiver={receiver_id}, Chat={chat_id}, Text={text}")

def save_picture_message(receiver_id, chat_id, file_info, message_text):
    print(f"Save picture message: Receiver={receiver_id}, Chat={chat_id}, FileInfo={file_info}, Text={message_text}")

def save_file_message(receiver_id, chat_id, file_info, message_text):
    print(f"Save file message: Receiver={receiver_id}, Chat={chat_id}, FileInfo={file_info}, Text={message_text}")

def download_file(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return {'url': url, 'size': len(r.content), 'content': r.content}
    except Exception as e:
        print(f"File download failed: {e}")
    return None

def set_error_delivery_status(message_id):
    print(f"Set error delivery status for message {message_id}")

@app.route('/webhook/<path:scope_id>', methods=['POST'])
@app.route('/webhook', defaults={'scope_id': ''}, methods=['POST'])
def webhook(scope_id):
    body = request.get_data()
    received_signature = request.headers.get('X-Signature')
    expected_signature = hmac.new(SECRET.encode(), body, hashlib.sha1).hexdigest()
    if not received_signature or received_signature != expected_signature:
        return 'Invalid hook signature', 401

    hookBody = request.get_json(silent=True)
    if not hookBody:
        abort(400, 'Invalid JSON body')

    accountId = hookBody.get('account_id')
    message = hookBody.get('message', {})
    msg = message.get('message', {})
    messageId = msg.get('id')
    messageType = msg.get('type')
    messageText = msg.get('text')
    conversation = message.get('conversation', {})
    messageChatId = conversation.get('client_id')
    messageAmoCrmChatId = conversation.get('id')
    fileLink = msg.get('media')
    receiver = message.get('receiver', {})
    receiverId = receiver.get('id')

    if messageType == 'text':
        save_text_message(receiverId, messageChatId, messageText)
    elif messageType == 'picture':
        downloadedFile = download_file(fileLink)
        save_picture_message(receiverId, messageChatId, downloadedFile, messageText)
    elif messageType == 'file':
        downloadedFile = download_file(fileLink)
        save_file_message(receiverId, messageChatId, downloadedFile, messageText)
    else:
        set_error_delivery_status(messageId)
        abort(400, 'Unsupported message type')

    return '', 200

def create_signature(secret, checksum, api_method, http_method='POST', content_type='application/json'):
    date_rfc = time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime())
    string_to_sign = f"{http_method}\n{checksum}\n{content_type}\n{date_rfc}\n{api_method}"
    return hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha1).hexdigest()

def bind_channel():
    path = f'/v2/origin/custom/{CHANNEL_ID}/connect'
    url = f'https://amojo.amocrm.ru{path}'
    body = {
        'account_id': AMOJO_ID,
        'title': 'MyWebhook',
        'hook_api_version': 'v2'
    }
    body_str = json.dumps(body)
    md5 = hashlib.md5(body_str.encode()).hexdigest()
    date = time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime())
    signature = create_signature(SECRET, md5, path)
    headers = {
        'Content-Type': 'application/json',
        'Content-MD5': md5,
        'Date': date,
        'X-Signature': signature
    }
    response = requests.post(url, data=body_str, headers=headers)
    if response.status_code == 200:
        scope_id = response.json().get('scope_id')
        print(f'Channel bound successfully! scope_id = {scope_id}')
    else:
        print(f'Failed to bind channel: {response.status_code} {response.text}')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--bind':
        bind_channel()
    else:
        app.run(host='0.0.0.0', port=80)
