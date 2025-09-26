# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y curl wget unzip libnss3 libatk1.0-0 \
    libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2 libxrandr2 \
    libxdamage1 libxcomposite1 libxext6 libxfixes3 libcairo2 libpango-1.0-0 \
    libpangocairo-1.0-0 libgtk-3-0 chromium

# Copy dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright + Chromium
RUN python -m playwright install --with-deps chromium

# Copy app code
COPY . .

# Expose port
ENV PORT=8000
EXPOSE 8000

# Run app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

