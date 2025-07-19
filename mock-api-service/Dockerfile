# Mock API Service - PersonaFlow
FROM python:3.12-slim

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install additional system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Synchronize dependencies
RUN uv sync --frozen

# Expose port for Cloud Run
EXPOSE 8080

# Run the mock API service
CMD ["uv", "run", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]