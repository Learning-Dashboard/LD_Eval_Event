# Use a lightweight Python base image
FROM python:3.9-slim

# Create and use the /app directory
WORKDIR /app

# Copy your requirements.txt in first so Docker can cache the pip install layer
COPY requirements.txt .

# Install your dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code into the container
COPY . .

# Expose port 5001 for your Flask/Gunicorn app to listen on the CONNECT component
EXPOSE 5001

#set timezone to madrid
ENV TZ=Europe/Madrid

# Run gunicorn for  "app:create_app()" factory function
CMD ["gunicorn", "-k", "gthread", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "25",  "app:create_app()"]
