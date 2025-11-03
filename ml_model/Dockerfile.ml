FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ml_model/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ml_model application files (this includes classes subdirectory)
COPY ml_model/ ./ml_model/

# Copy data directory
COPY data/ ./data/

# Expose port for API (if needed in the future)
EXPOSE 5000

# Run the ML pipeline
CMD ["python", "ml_model/main.py"]
