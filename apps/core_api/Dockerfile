# apps/core_api/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Security & optimization headers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed for git-based python packages
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install project dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
RUN playwright install chromium && playwright install-deps chromium

# Copy application code
COPY . .

# Expose standard FastAPI port
EXPOSE 8000

# Run Uvicorn in production mode (no --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
