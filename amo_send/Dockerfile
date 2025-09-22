FROM python:3.9-slim

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt -q

# Копируем код
COPY . .

ENV PATH="/app/venv/bin:$PATH"

# Запуск Uvicorn (Traefik будет проксировать на порт 8000)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
