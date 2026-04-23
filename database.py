from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os, sys

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    sys.exit(
        "\n❌  DATABASE_URL is not set.\n"
        "    Open your .env file and set it like:\n"
        "    DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/dashboard_db\n"
    )

try:
    engine = create_engine(DATABASE_URL)
    # Test the connection immediately on startup
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅  Database connected successfully.")
except Exception as e:
    sys.exit(
        f"\n❌  Could not connect to the database.\n"
        f"    Error: {e}\n\n"
        f"    Check that:\n"
        f"    1. PostgreSQL is running\n"
        f"    2. The database 'dashboard_db' exists  →  run: createdb dashboard_db\n"
        f"    3. Your password in .env is correct\n"
        f"    4. DATABASE_URL format: postgresql://user:password@localhost:5432/dbname\n"
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()