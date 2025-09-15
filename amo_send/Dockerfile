FROM python:3.9-slim

WORKDIR /app

# 1. Копируем requirements.txt (меняется редко)
COPY requirements.txt .

# ---------- Устанавливаем authbind ----------
RUN apt-get update \
    && apt-get install -y --no-install-recommends authbind \
    && rm -rf /var/lib/apt/lists/*

# 2. Устанавливаем зависимости (меняется только при изменении requirements.txt)
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt -q

# 3. Копируем код (меняется часто)
COPY . .

ENV PATH="/app/venv/bin:$PATH"

# Команда запуска: как вы указали локально (authbind --deep python3 server.py)
CMD ["authbind","--deep","python","-m", "main"]

