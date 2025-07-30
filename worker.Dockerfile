# Use Python 3.12 slim image
FROM python:3.12-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first (for better Docker layer caching)
COPY pyproject.toml ./

# Copy app structure for package installation
COPY app/ ./app/

# Install the package and dependencies (not editable for production)
RUN pip install --no-cache-dir .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash worker && \
    chown -R worker:worker /app
USER worker

# Set environment variables
ENV PYTHONUNBUFFERED=1

# # Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD python -c "from app.worker.hatchet_client import hatchet; print('Worker healthy')" || exit 1

# Run the worker
CMD ["python", "-m", "app.run_worker"]
