FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for psycopg2 and some ML libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer — only rebuilds if requirements.txt changes)
COPY request/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY request/backend/ ./backend/
COPY request/data/ ./data/

# Set Python path so imports work
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (overridden by docker-compose for different services)
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
