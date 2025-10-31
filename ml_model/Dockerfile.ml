FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the classes directory and data
COPY classes/ ./classes/
COPY data/ ./data/

# Expose port for API (if needed in the future)
EXPOSE 5000

# Keep container running and ready to serve predictions
CMD ["python", "-c", "print('ML Model service is ready'); import time; time.sleep(infinity)"]
