#!/usr/bin/env python3
"""
Diagnostic Health Check Script for Multi-Agent AI Disaster Framework (Phase 0)
Validates:
1. Python dependencies (FastAPI, Celery, Redis, PyTorch, Transformers, spaCy, ChromaDB, PRAW, etc.)
2. Redis connectivity
3. Database connectivity (PostgreSQL / SQLite fallback)
"""

import sys
import os
from pathlib import Path

# Add current and backend directories to path
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "backend"))

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_python():
    print_header("1. Python Environment Check")
    print(f"Python Version: {sys.version}")
    print(f"Executable:     {sys.executable}")
    major, minor = sys.version_info.major, sys.version_info.minor
    if major >= 3 and minor >= 10:
        print("  [OK] Python version meets requirements (>= 3.10)")
        return True
    else:
        print("  [WARN] Python >= 3.10 is recommended.")
        return True

def check_libraries():
    print_header("2. Package & Library Verification")
    packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("celery", "Celery"),
        ("redis", "Redis Client"),
        ("sqlalchemy", "SQLAlchemy"),
        ("psycopg2", "psycopg2-binary"),
        ("torch", "PyTorch"),
        ("transformers", "Hugging Face Transformers"),
        ("spacy", "spaCy"),
        ("sentence_transformers", "Sentence-Transformers"),
        ("chromadb", "ChromaDB"),
        ("geopy", "GeoPy"),
        ("praw", "PRAW (Reddit)"),
        ("requests", "Requests"),
        ("httpx", "HTTPX"),
        ("feedparser", "Feedparser"),
        ("pydantic", "Pydantic"),
        ("dotenv", "python-dotenv"),
    ]

    all_ok = True
    for mod_name, label in packages:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "installed")
            print(f"  [OK] {label:<28} (v{ver})")
        except ImportError as e:
            print(f"  [MISSING] {label:<28} -> {e}")
            all_ok = False

    return all_ok

def check_redis():
    print_header("3. Redis Connectivity Check")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"Connecting to Redis at: {redis_url}...")
    try:
        import redis
        # Support both Redis 6+/7+ (RESP3) and Redis 5.x (RESP2)
        try:
            client = redis.from_url(redis_url, socket_timeout=3.0, protocol=2)
        except TypeError:
            client = redis.from_url(redis_url, socket_timeout=3.0)
            
        pong = client.ping()
        if pong:
            # Test write/read
            client.set("disaster_health_check_key", "healthy_ok", ex=10)
            val = client.get("disaster_health_check_key")
            val_str = val.decode() if isinstance(val, bytes) else val
            print(f"  [OK] Redis Ping Succeeded (PONG: {pong})")
            print(f"  [OK] Redis Read/Write Test Verified (Value: '{val_str}')")
            return True
        else:
            print("  [FAIL] Redis did not respond with PONG.")
            return False
    except Exception as ex:
        print(f"  [FAIL] Could not connect to Redis: {ex}")
        print("  -> Please verify Redis is running locally or start it via docker-compose up redis -d")
        return False

def check_database():
    print_header("4. Database Connectivity Check")
    pg_url = os.getenv("DATABASE_URL_SYNC", "postgresql://disaster_user:disaster_pass@localhost:5432/disaster_db")
    sqlite_url = "sqlite:///./disaster_app.db"
    
    import sqlalchemy
    from sqlalchemy import text

    # Try PostgreSQL first
    print(f"Testing PostgreSQL connection ({pg_url})...")
    pg_success = False
    try:
        engine_pg = sqlalchemy.create_engine(pg_url, connect_args={"connect_timeout": 3})
        with engine_pg.connect() as conn:
            result = conn.execute(text("SELECT 1;")).scalar()
            if result == 1:
                print("  [OK] PostgreSQL connection succeeded and verified (SELECT 1).")
                pg_success = True
    except Exception as ex:
        print(f"  [NOTICE] PostgreSQL not reachable: {ex}")
        print("  -> When ready, you can start PostgreSQL using `docker-compose up -d postgres`.")

    # Always test SQLite fallback capability
    print(f"\nTesting Local SQLite Fallback connection ({sqlite_url})...")
    sqlite_success = False
    try:
        engine_sqlite = sqlalchemy.create_engine(sqlite_url)
        with engine_sqlite.connect() as conn:
            result = conn.execute(text("SELECT 1;")).scalar()
            if result == 1:
                print("  [OK] SQLite fallback engine functional and verified (SELECT 1).")
                sqlite_success = True
    except Exception as ex:
        print(f"  [FAIL] SQLite error: {ex}")

    return pg_success or sqlite_success

def check_spacy_model():
    print_header("5. spaCy Model Check")
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp("Severe flooding reported in Mumbai, Maharashtra.")
        ents = [(e.text, e.label_) for e in doc.ents]
        print(f"  [OK] Model 'en_core_web_sm' loaded successfully.")
        print(f"  [OK] Sample NER parse: '{doc.text}' -> {ents}")
        return True
    except Exception as ex:
        print(f"  [MISSING] spaCy model 'en_core_web_sm' not found: {ex}")
        print("  -> Run: python -m spacy download en_core_web_sm")
        return False

def main():
    print("\n" + "#" * 60)
    print("  MULTI-AGENT AI DISASTER FRAMEWORK - HEALTH CHECK")
    print("#" * 60)

    py_ok = check_python()
    libs_ok = check_libraries()
    redis_ok = check_redis()
    db_ok = check_database()
    spacy_ok = check_spacy_model()

    print_header("SUMMARY OF SERVICES")
    print(f"  Python Environment:     {'[PASS]' if py_ok else '[FAIL]'}")
    print(f"  Required Libraries:     {'[PASS]' if libs_ok else '[PARTIAL/MISSING]'}")
    print(f"  Redis Server:           {'[PASS]' if redis_ok else '[FAIL]'}")
    print(f"  Database Engine:        {'[PASS]' if db_ok else '[FAIL]'}")
    print(f"  spaCy NER Model:        {'[PASS]' if spacy_ok else '[PENDING DOWNLOAD]'}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
