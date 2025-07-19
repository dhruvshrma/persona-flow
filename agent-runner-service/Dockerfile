# Orchestrator Service - PersonaFlow
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

# Run the orchestrator service
CMD ["uv", "run", "uvicorn", "app.orchestrator:app", "--host", "0.0.0.0", "--port", "8080"]