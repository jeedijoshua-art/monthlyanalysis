from database import engine, Base
import models
from sqlalchemy import text

try:
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("DATABASE CONNECTION: PASS")
        
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("TABLE CREATION: PASS")
except Exception as e:
    print("DATABASE CONNECTION: FAIL")
    print(f"ERROR: {type(e).__name__} - {e}")
