# apps/core_api/Dockerfile
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

# Expose standard FastAPI port
EXPOSE 8000

# Run Uvicorn in production mode (no --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
