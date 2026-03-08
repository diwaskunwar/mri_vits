FROM python:3.11-slim

WORKDIR /app

# Install system deps (OpenCV headless needs these)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock /app/

# Install deps
RUN uv sync --no-dev

# Copy serve script
COPY serve.py /app/serve.py

# Expose Ray Serve port
EXPOSE 8001

# Start Ray Serve
CMD ["uv", "run", "python", "serve.py", "--port", "8001"]
