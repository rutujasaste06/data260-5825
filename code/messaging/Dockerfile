FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The actual command run (worker vs api) is set per-service in docker-compose.yml
CMD ["python", "worker.py"]
