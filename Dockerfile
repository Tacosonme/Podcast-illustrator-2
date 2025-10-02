# Use Python 3.11 with Ubuntu base for FFmpeg support
FROM python:3.11-slim

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy start script
COPY start.sh .
RUN chmod +x start.sh

# Create uploads directory
RUN mkdir -p /tmp/uploads

# Start command using bash script
CMD ["./start.sh"]
