FROM python:3.10-slim

WORKDIR /app

# Install Streamlit for the admin panel
RUN pip install streamlit sqlalchemy pymysql pandas

COPY . .

# The command to start the admin panel
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]