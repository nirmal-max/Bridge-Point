FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies from the backend folder
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Command to run (app.main is inside backend/app/main.py which is now in /app/app/main.py)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
