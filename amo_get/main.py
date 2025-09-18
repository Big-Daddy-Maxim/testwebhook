from fastapi import FastAPI, Request, HTTPException
import requests
import json
import os
from dotenv import load_dotenv
import logging
import aiohttp

# --- Логгер ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- Конфиг ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_URL = "http://telegram_bot:8000"

app = FastAPI()

async def analyze_and_forward_message(msg_block: dict) -> bool:
    """Анализирует тело сообщения, извлекает tg_id и текст, отправляет в telegram_bot через API."""
    logger.info(f"[ANALYZE] Received msg_block: {json.dumps(msg_block, ensure_ascii=False)}")
    
    # Шаг 1: Извлечение tg_id
    if 'receiver' in msg_block and 'client_id' in msg_block['receiver']:
        tg_id = msg_block['receiver']['client_id']
        logger.info(f"[ANALYZE] Found tg_id: {tg_id}")
    else:
        logger.error("[ANALYZE] No receiver.client_id found")
        return False

    # Шаг 2: Извлечение текста
    if 'message' in msg_block and 'text' in msg_block['message']:
        text = msg_block['message']['text']
        logger.info(f"[ANALYZE] Found text: {text}")
    else:
        logger.error("[ANALYZE] No message.text found")
        return False

    # Шаг 3: Формирование payload
    payload = {
        "tg_id": tg_id,
        "text": text
    }
    logger.info(f"[ANALYZE] Prepared payload: {json.dumps(payload, ensure_ascii=False)}")

    # Шаг 4: Отправка API-запроса в telegram_bot
    url = f"{TELEGRAM_BOT_URL}/send_to_tg"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"[FORWARD] Successfully sent to telegram_bot: {await response.text()}")
                    return True
                else:
                    logger.error(f"[FORWARD] Error from telegram_bot: status={response.status}, response={await response.text()}")
                    return False
    except Exception as e:
        logger.critical(f"[FORWARD] Failed to connect to telegram_bot: {e}")
        return False

@app.api_route("/webhook/{scope_id}", methods=["GET", "POST"])
@app.api_route("/webhook/", methods=["GET", "POST"])
async def webhook(scope_id: str = "", request: Request = None):
    if request.method == "GET":
        logger.info(f"PING ok (scope_id={scope_id}) from {request.client.host}")
        return "ok"
    try:
        data = await request.json()
        logger.info(f"[INCOMING JSON] {json.dumps(data, ensure_ascii=False)}")
        if not data or "message" not in data:
            logger.warning("[ERROR] Пустой или не-JSON запрос")
            raise HTTPException(status_code=400, detail="bad request")

        msg_block = data["message"]
        logger.info(f"[PARSED MESSAGE BLOCK] {json.dumps(msg_block, ensure_ascii=False)}")

        # Вызов новой функции анализа и пересылки
        success = await analyze_and_forward_message(msg_block)
        if success:
            logger.info("[SUCCESS] Message forwarded to telegram_bot")
        else:
            logger.error("[FAIL] Message forwarding failed")

        return {"success": success}
    except Exception as e:
        logger.error(f"[CRITICAL] Ошибка обработки webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/favicon.ico")
async def favicon():
    return "", 204

if __name__ == "__main__":
    import uvicorn
    logger.info("[START] amo_get starting...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
