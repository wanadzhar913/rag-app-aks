FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && pip install --upgrade pip \
    && pip install uv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m appuser

COPY pyproject.toml ./
RUN uv venv && . .venv/bin/activate && uv pip install -e .

COPY pipeline/ ./pipeline/

RUN chown -R appuser:appuser /app

USER appuser

CMD ["/app/.venv/bin/python", "-m", "pipeline.worker"]
