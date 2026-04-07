FROM python:3.12-slim

WORKDIR /app

# Install WeasyPrint system dependencies and standard web fonts
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    fontconfig \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install uv

# Copy package config and install dependencies
COPY pyproject.toml ./
RUN uv pip install --system -e .

# Copy application files
COPY . .

EXPOSE 8002

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}
