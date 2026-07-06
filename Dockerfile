# 1. Use a slim Python 3.12 image
FROM python:3.12-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# 3. Install system dependencies
# ffmpeg is essential for your TranscriptionService/media processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 4. Set work directory
WORKDIR /app

# 5. Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the entire application
COPY . .

# 7. Create the uploads directory and ensure permissions
RUN mkdir -p /app/uploads && chmod 755 /app/uploads

# 8. Expose the port
EXPOSE 8000

# 9. Run the application
# Use 'uvicorn' directly. Note: Do NOT use 'reload=True' in production.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]