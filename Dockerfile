# Base image with essential system dependencies
FROM python:3.11.4-slim-bullseye AS base

# Set environment variables
ENV POETRY_VERSION=1.8.2 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PATH="/opt/poetry/bin:$PATH"

# Install necessary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip3 install "poetry==$POETRY_VERSION"

# Create working directory
WORKDIR /app/src

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock ./

# Install dependencies using a cache mount
RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main

# Remove build dependencies to reduce image size
RUN apt-get purge -y gcc && rm -rf /var/lib/apt/lists/* /tmp/poetry_cache

# Copy application code
COPY . .

# Run the application
CMD ["python3", "-m", "app"]

# Development stage
FROM base AS dev

# Install all dependencies including dev dependencies
RUN --mount=type=cache,target=/tmp/poetry_cache poetry install
