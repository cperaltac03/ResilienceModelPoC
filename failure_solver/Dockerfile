FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY failure_solver/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY failure_solver ./failure_solver

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "failure_solver/app.py"]
