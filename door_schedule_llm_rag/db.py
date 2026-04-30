import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_env, BASE_DIR

# Database URL format: postgresql://user:password@localhost/dbname
# SQLite fallback: sqlite:///app.db
DB_URL = get_env("DATABASE_URL", f"sqlite:///{BASE_DIR}/app.db")

# In Streamlit, connection pooling might need config, but for SQLite we just avoid check_same_thread
if DB_URL.startswith("sqlite"):
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DB_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import all models here so they are registered with Base
    import models
    Base.metadata.create_all(bind=engine)
