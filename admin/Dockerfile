FROM python:3.10-slim

WORKDIR /app

# Install dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The command to start the admin panel
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]