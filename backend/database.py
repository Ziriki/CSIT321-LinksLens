import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables securely
load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "LinksLens-DB")
MYSQL_HOST = os.getenv("MYSQL_HOST", "db") 

# URL-encode credentials to safely handle special characters (e.g. @, #, $) in passwords
SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}"
    f"@{MYSQL_HOST}:3306/{MYSQL_DATABASE}"
)

# Initialize the SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency block to open and close DB connections automatically
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()