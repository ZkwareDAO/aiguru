# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN cd backend && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Set environment variables
ENV PYTHONPATH="/app/backend"
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE $PORT

# Change to backend directory and start the application
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
