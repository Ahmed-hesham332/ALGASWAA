# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies required for mysqlclient and potential others
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Switch to the project folder containing manage.py
WORKDIR /app/starlink_isp

# Expose port 8000
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "starlink_isp.wsgi:application", "--bind", "0.0.0.0:8000"]
