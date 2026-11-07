# MedClaim Rx — Production Container Image
FROM python:3.12-slim

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and seed assets
COPY app/ ./app/
COPY eval/ ./eval/
COPY data/ ./data/
COPY pyproject.toml .
COPY README.md .
COPY streamlit_app.py .

# Create persistent storage directories
RUN mkdir -p /app/data /app/logs /app/.chroma

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8010 8501

# Default command launches the Streamlit desk
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
