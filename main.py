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

# --- Webhook для загрузки картинки в amoCRM ---
@app.post("/upload_to_amocrm")
async def upload_to_amocrm(request: Request):
    data = await request.json()
    entity_id = data.get("entity_id")
    entity_type = data.get("entity_type")
    filename = data.get("filename")
    
    if not all([entity_id, entity_type, filename]):
        raise HTTPException(status_code=400, detail="Отсутствуют параметры")
    
    profile_dir = Path(__file__).parent.parent / "Data" / "profile_picture"
    file_path = profile_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    upload_url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/api/v4/{entity_type}/{entity_id}/files"
    headers = {"Authorization": f"Bearer {AMOCRM_TOKEN}"}
    files = {"file": (filename, open(file_path, "rb"), "image/jpeg")}
    
    resp = requests.post(upload_url, headers=headers, files=files)
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    
    return {"message": "success"}

# --- Маршрут для сервировки аватаров ---
@app.get("/profile_picture/{filename}")
async def serve_profile_picture(filename: str):
    profile_dir = Path(__file__).parent.parent / "Data" / "profile_picture"
    file_path = profile_dir / filename
    
    if not file_path.exists():
        logger.error(f"Файл не найден: {filename}")
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    logger.info(f"Сервировка файла: {filename}")
    return FileResponse(file_path)

# --- Favicon (пустой, чтобы избежать ошибок) ---
@app.get("/favicon.ico")
async def favicon():
    return "", 204

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=80)
