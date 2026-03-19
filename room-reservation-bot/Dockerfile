FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist the SQLite database across container restarts
VOLUME ["/app/data"]

CMD ["python", "-m", "bot.main"]
