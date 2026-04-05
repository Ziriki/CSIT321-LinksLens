FROM python:3.11-slim

WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Pip install everything listed in the file
RUN pip install --no-cache-dir -r requirements.txt

# Download the correct Chromium binaries for the installed playwright version
RUN playwright install chromium

# Copy the rest of the application code
COPY . .

# Start the backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]