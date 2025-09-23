FROM python:3.9-slim

WORKDIR /app

#  устанавка зависимостей 
COPY requirements.txt .
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt -q

# копируем код
COPY . .

ENV PATH="/app/venv/bin:$PATH"

CMD ["python", "user_db.py"]
