FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Single worker keeps free-tier Gemini requests under the per-minute limit.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 120 app.main:app
