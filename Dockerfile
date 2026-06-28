# Use a base image matching the project's Python version (3.11.9)
FROM python:3.11.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 for Flask
EXPOSE 5000

# Command to run the Flask application
CMD ["python", "app.py"]
