FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for output
RUN mkdir -p /app/alerts /app/media /app/certs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OUTPUT_DIR=/app/alerts
ENV MEDIA_DIR=/app/media

# Expose port for health checks
EXPOSE 8001

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting CAP Generator..."\n\
python cap_generator.py --daemon\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]