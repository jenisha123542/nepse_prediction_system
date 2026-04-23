"""
Run this BEFORE starting the server to verify everything is configured correctly.
Usage: python check_setup.py
"""
import sys, os
from dotenv import load_dotenv

load_dotenv()

print("\n🔍 Checking your setup...\n")
errors = []

# 1. Check .env
if not os.path.exists(".env"):
    errors.append("❌  .env file not found.")
else:
    print("✅  .env file found")

# 2. Check DATABASE_URL
db_url = os.getenv("DATABASE_URL", "")
if not db_url:
    errors.append("❌  DATABASE_URL is not set in .env")
else:
    print(f"✅  DATABASE_URL is set → {db_url.split('@')[-1]}")  # print only host/db, hide password

# 3. Check SECRET_KEY
sk = os.getenv("SECRET_KEY", "")
if not sk or sk == "your-super-secret-key-change-this":
    errors.append("❌  SECRET_KEY is weak or not set. Use a random 32+ char string.")
else:
    print("✅  SECRET_KEY is set")

# 4. Test DB connection
if db_url:
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅  PostgreSQL connection successful")

        # Check if tables exist
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public'"
            ))
            tables = [r[0] for r in result]
            if "users" in tables:
                count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
                print(f"✅  'users' table exists ({count} users in DB)")
            else:
                print("⚠️   'users' table not found — will be created when server starts")

    except Exception as e:
        errors.append(f"❌  Cannot connect to PostgreSQL:\n    {e}")
        errors.append("    → Make sure PostgreSQL is running:  sudo service postgresql start")
        errors.append("    → Make sure the DB exists:          createdb nepse_db")
        errors.append("    → Grant permissions:                GRANT ALL PRIVILEGES ON DATABASE nepse_db TO jenisha;")

# 5. Check packages
required = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("sqlalchemy", "sqlalchemy"),
    ("passlib", "passlib"),
    ("jose", "python-jose[cryptography]"),
    ("dotenv", "python-dotenv"),
    ("pydantic", "pydantic[email]"),
]
for mod, pkg in required:
    try:
        __import__(mod)
        print(f"✅  {pkg} installed")
    except ImportError:
        errors.append(f"❌  Missing: {pkg}  →  pip install {pkg}")

# Summary
print()
if errors:
    print("── ISSUES FOUND ──────────────────────────────")
    for e in errors:
        print(e)
    print("\nFix the above, then run: uvicorn main:app --reload\n")
    sys.exit(1)
else:
    print("── ALL GOOD ──────────────────────────────────")
    print("Run:  uvicorn main:app --reload")
    print("Docs: http://localhost:8000/docs\n")