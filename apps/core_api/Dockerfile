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


# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose standard FastAPI port
EXPOSE 8000

# Run Alembic migrations then start Uvicorn
CMD ["./entrypoint.sh"]
