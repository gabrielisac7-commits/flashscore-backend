# Use lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy dependencies first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (Railway/Heroku injects $PORT)
EXPOSE 8000

# Start app (main.py handles $PORT)
CMD ["python", "main.py"]
