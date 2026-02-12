# We use this specific image because it has the Browsers (Chrome) pre-installed for your scanner
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Install the tools your backend needs
RUN pip install fastapi uvicorn sqlalchemy pymysql requests python-multipart beautifulsoup4

# Copy your code into the container
COPY . .

# The command to start the backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]