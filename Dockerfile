FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y curl unzip libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libxdamage1 libxfixes3 libxcomposite1 libxrandr2 libasound2 libpango-1.0-0 libcairo2 fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .
RUN python manage.py collectstatic --noinput
CMD ["sh", "-c", "gunicorn demo.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
