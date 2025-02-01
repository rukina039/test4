# Use a lightweight Python 3.11 image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Expose port 8080 for GCP
EXPOSE 8080

# Run with gunicorn on port 8080
CMD ["gunicorn", "--bind=0.0.0.0:8080", "app:app"]
