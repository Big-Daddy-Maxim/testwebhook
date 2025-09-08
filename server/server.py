from flask import Flask, request
import requests
import json
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# --- логгер -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- конфиг -------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)

# -----------------------------------------------------------
@app.errorhandler(400)
def handle_bad_request(err):
    logger.info(f"400 | {err} | IP {request.remote_addr}")
    return "bad request", 400


@app.route("/webhook", defaults={"scope_id": ""}, methods=["POST", "GET"])
@app.route("/webhook/<scope_id>", methods=["POST", "GET"])
def webhook(scope_id):
    if request.method == "GET":
        logger.info(f"PING ok (scope_id={scope_id}) from {request.remote_addr}")
        return "ok", 200

    # --- читаем JSON ---------------------------------------
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        logger.warning("Пустой или не-JSON запрос")
        return "bad", 400

    logger.info(f"RAW: {json.dumps(data, ensure_ascii=False)}")   # ensure_ascii=False ─ русские видны в логе

    # --- вытаскиваем нужное -------------------------------
    msg_block   = data["message"]
    tg_id       = msg_block["receiver"]["client_id"]        # chat_id пользователя в Telegram
    text        = msg_block["message"]["text"]              # сам текст
    sender_id   = msg_block["sender"]["id"]                 # id автора в amoCRM

    # --- отправляем в Telegram -----------------------------
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # json=... → requests сам сделает UTF-8 и заголовок
    resp = requests.post(
        telegram_url,
        json={
            "chat_id": tg_id,
            "text":    text 
        }
    )

    if resp.status_code == 200:
        logger.info(f"Отправлено в TG ({tg_id}): {text}")
    else:
        logger.error(f"TG error {resp.status_code}: {resp.text}")

    return "success", 200


@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
