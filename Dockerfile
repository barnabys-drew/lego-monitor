FROM python:3.14-slim

WORKDIR /app

# Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY src/ ./src/

# Data volume
RUN mkdir -p ./data

# Run scraper
CMD ["python", "src/lego_scraper.py"]
