FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY rules_manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY rules_manager ./rules_manager

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "rules_manager.app:app", "--host", "0.0.0.0", "--port", "8000"]