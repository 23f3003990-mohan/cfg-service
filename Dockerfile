FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# OS-level layer (highest non-CLI precedence)
ENV APP_PORT=8732 APP_WORKERS=1 APP_DEBUG=false
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8732}"]
