FROM python:3.9-slim

WORKDIR /app

# 1. Копируем requirements.txt (меняется редко)
COPY requirements.txt .

# 2. Устанавливаем зависимости (меняется только при изменении requirements.txt)
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt -q

# 3. Копируем код (меняется часто)
COPY . .

ENV PATH="/app/venv/bin:$PATH"

# Команда запуска: как вы указали локально
CMD ["python", "-m", "main"]