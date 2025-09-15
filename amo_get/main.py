from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
import requests
import json
import os
from dotenv import load_dotenv
import logging
from pathlib import Path  # Импортируем Path

load_dotenv()

# --- Логгер ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- Конфиг ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN")  # Добавьте в .env, если нужно
AMOCRM_TOKEN = os.getenv("AMOCRM_TOKEN")  # Добавьте в .env для авторизации

app = FastAPI()

# --- Webhook для amoCRM (адаптировано под FastAPI) ---
@app.api_route("/webhook/{scope_id}", methods=["GET", "POST"])
@app.api_route("/webhook/", methods=["GET", "POST"])
async def webhook(scope_id: str = "", request: Request = None):
    if request.method == "GET":
        logger.info(f"PING ok (scope_id={scope_id}) from {request.client.host}")
        return "ok"
    
    data = await request.json()
    if not data or "message" not in data:
        logger.warning("Пустой или не-JSON запрос")
        raise HTTPException(status_code=400, detail="bad request")
    
    logger.info(f"RAW: {json.dumps(data, ensure_ascii=False)}")
    
    msg_block = data["message"]
    tg_id = msg_block["receiver"]["client_id"]
    text = msg_block["message"]["text"]
    sender_id = msg_block["sender"]["id"]
    
    # потом удалить
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    resp = requests.post(
        telegram_url,
        json={
            "chat_id": tg_id,
            "text": text
        }
    )
    
    if resp.status_code == 200:
        logger.info(f"Отправлено в TG ({tg_id}): {text}")
    else:
        logger.error(f"TG error {resp.status_code}: {resp.text}")
    
    return "success"


# --- Favicon (тоже потом удалить) ---
@app.get("/favicon.ico")
async def favicon():
    return "", 204

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80) 