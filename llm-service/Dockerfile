# LLM Service - PersonaFlow (GPU-enabled)
FROM python:3.12-slim

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install additional system dependencies for LLM operations
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Synchronize dependencies
RUN uv sync --frozen

# Note: Will integrate with your existing ollama-backend
# TODO: Copy ollama configuration and model files

# Expose port for Cloud Run
EXPOSE 8080

# Run the LLM service
CMD ["uv", "run", "uvicorn", "app.llm:app", "--host", "0.0.0.0", "--port", "8080"]