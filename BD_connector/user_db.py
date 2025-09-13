# BD_connector/user_db.py
import os
import json
import logging
from typing import List, Dict, Optional

# ─── ЛОГГЕР ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

# ─── ПУТЬ К JSON ───────────────────────────────────────────
DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data'))
USER_FILE = os.path.join(DATA_DIR, 'user_conversations.json')

# ─── ВНУТРЕННИЕ ВСПОМОГАТЕЛЬНЫЕ ───────────────────────────
def _load_users() -> List[Dict]:
    """Возвращает список пользователей из JSON или пустой список при ошибке/отсутствии файла."""
    if not os.path.exists(USER_FILE):
        logging.info('Файл БД отсутствует — возвращён пустой список.')
        return []
    try:
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            raw = f.read().strip()
            return json.loads(raw) if raw else []
    except Exception as e:
        logging.error(f'Ошибка чтения БД: {e}')
        return []

def _save_users(users: List[Dict]) -> None:
    """Сохраняет список пользователей в JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)
    logging.info(f'Сохранено пользователей: {len(users)}')

# ─── БАЗОВЫЕ ОПЕРАЦИИ ─────────────────────────────────────
def find_user_by_tg_id(tg_id: str) -> Optional[Dict]:
    """Ищет и возвращает пользователя по Telegram-ID."""
    for user in _load_users():
        if user.get('tg_id') == tg_id:
            logging.info(f'Найден пользователь tg_id={tg_id}')
            return user
    logging.info(f'Пользователь tg_id={tg_id} не найден')
    return None

def find_user_by_amocrm_id(amocrm_id: str) -> Optional[Dict]:
    """Ищет и возвращает пользователя по Telegram-ID."""
    for user in _load_users():
        if user.get('amocrm_id') == amocrm_id:
            logging.info(f'Найден пользователь amocrm_id={amocrm_id}')
            return user
    logging.info(f'Пользователь amocrm_id={amocrm_id} не найден')
    return None

# ---------- 1. СОЗДАНИЕ ---------- #
def create_user(
    amocrm_id: str = None,
    tg_id: str = None,
    name: str = None,
    username: str = None,
    avatar: str = None,
    email: str = None,
    phone: str = None
) -> Dict:
    """Создаёт нового пользователя и сохраняет его в JSON."""
    users = _load_users()

    new_user = {
        'amocrm_id': amocrm_id,
        'tg_id'    : tg_id,
        'name'     : name,
        'username' : username,
        'avatar'   : avatar,
        'email'    : email,
        'phone'    : phone
    }
    users.append(new_user)
    _save_users(users)
    logging.info(f'Создан новый пользователь tg_id={tg_id}')
    return new_user

