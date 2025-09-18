from fastapi import FastAPI, Request, HTTPException
import requests
import json
import os
from dotenv import load_dotenv
import logging

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

app = FastAPI()

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

        # Проверка структуры блока receiver
        if "receiver" not in msg_block or "client_id" not in msg_block["receiver"]:
            logger.error(f"[ERROR] Отсутствует receiver или client_id в msg_block: {msg_block}")
            raise HTTPException(status_code=400, detail="missing receiver.client_id")

        tg_id = msg_block["receiver"]["client_id"]
        text = msg_block["message"].get("text", "")
        sender_id = msg_block["sender"].get("id", "unknown")

        logger.info(f"[READY TO SEND] To TG chat_id={tg_id}, text='{text}', sender={sender_id}")

        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        logger.info(f"[HTTP REQUEST] POST {telegram_url} | Payload: {{'chat_id': {tg_id}, 'text': '{text}'}}")
        try:
            resp = requests.post(
                telegram_url,
                json={
                    "chat_id": tg_id,
                    "text": text
                }
            )
            logger.info(f"[TELEGRAM RESPONSE] Status={resp.status_code} | Text={resp.text}")
        except Exception as e:
            logger.error(f"[CRITICAL] Ошибка запроса к Telegram API: {e}")
            raise HTTPException(status_code=500, detail=f"Telegram request error: {e}")

        if resp.status_code == 200:
            logger.info(f"[SUCCESS] Отправлено в TG ({tg_id}): {text}")
        else:
            logger.error(f"[FAIL] TG error {resp.status_code}: {resp.text}")

        return {"success": resp.status_code == 200, "telegram_status": resp.status_code}
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
