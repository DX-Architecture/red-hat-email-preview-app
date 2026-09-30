# Python + Chromium for Playwright (OpenShift-friendly)
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    DB_PATH=/data/email_preview.db \
    MAILPIT_API_URL=http://mailpit:8025 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

COPY config.py .
COPY database/ database/
COPY workers/ workers/
COPY app/ app/
COPY .streamlit/ .streamlit/

RUN mkdir -p /data && chmod -R g+rwX /data /app

EXPOSE 8501

CMD ["streamlit", "run", "app/dashboard.py", "--server.address=0.0.0.0", "--server.port=8501"]
