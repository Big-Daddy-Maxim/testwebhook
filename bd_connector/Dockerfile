FROM python:3.9-slim

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости (добавьте aio_pika в requirements.txt)
COPY requirements.txt .
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt -q

# Копируем код
COPY . .

ENV PATH="/app/venv/bin:$PATH"

# Запуск user_db.py как основной процесс (потребитель RabbitMQ)
CMD ["python", "user_db.py"]
