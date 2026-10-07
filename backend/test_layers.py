import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
db_url_raw = os.environ.get("DATABASE_URL")
if not db_url_raw:
    print("NO DATABASE_URL FOUND")
    exit(1)

parsed = urlparse(db_url_raw)
print("=== STEP 1: PARSING ===")
print(f"scheme={parsed.scheme}")
print(f"host={parsed.hostname}")
print(f"port={parsed.port}")
print(f"database={parsed.path}")
print(f"query={parsed.query}")

print("\n=== STEP 2: PSYCOPG2 DIRECTLY ===")
try:
    import psycopg2
    conn = psycopg2.connect(db_url_raw, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    res = cur.fetchone()
    print("psycopg2 SELECT 1:", res[0])
    conn.close()
except Exception as e:
    print("psycopg2 ERROR:", type(e).__name__, "-", str(e).strip())

print("\n=== STEP 3: PSYCOPG DIRECTLY ===")
try:
    import psycopg
    conn = psycopg.connect(db_url_raw.replace('postgres://', 'postgresql://'), connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    res = cur.fetchone()
    print("psycopg SELECT 1:", res[0])
    conn.close()
except Exception as e:
    print("psycopg ERROR:", type(e).__name__, "-", str(e).strip())

print("\n=== STEP 4: SQLALCHEMY ===")
try:
    from sqlalchemy import create_engine, text
    sa_url = db_url_raw
    if sa_url.startswith('postgres://'):
        sa_url = sa_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif sa_url.startswith('postgresql://'):
        sa_url = sa_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
        
    engine = create_engine(sa_url)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1;")).fetchone()
        print("SQLAlchemy SELECT 1:", res[0])
except Exception as e:
    print("SQLAlchemy ERROR:", type(e).__name__, "-", str(e).strip())
