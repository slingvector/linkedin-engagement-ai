# apps/ai_engine/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Security & optimization headers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install project dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Expose secondary FastAPI port
EXPOSE 8001

# Run Uvicorn in production mode (no --reload)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
