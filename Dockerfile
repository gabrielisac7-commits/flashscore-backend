FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for Playwright + Chromium
RUN apt-get update && apt-get install -y wget gnupg curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN pip install playwright && playwright install --with-deps chromium

# Copy app
COPY . .

# Expose port
EXPOSE 8080

# Run app (PORT comes from Railway, fallback to 8080 locally)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
