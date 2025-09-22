FROM python:3.9-slim

WORKDIR /app

# 1. Копируем requirements.txt
COPY requirements.txt .

# 2. Устанавливаем зависимости
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt -q

# 3. Копируем код
COPY . .

ENV PATH="/app/venv/bin:$PATH"

# Запуск основного скрипта (aiogram polling), FastAPI проксируется Traefik
CMD ["python", "main.py"]
