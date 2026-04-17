import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

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

# pool_pre_ping: test connection before using it (auto-reconnects stale connections)
# pool_recycle: discard connections older than 1 hour (MySQL default wait_timeout is 8h)
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()