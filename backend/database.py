import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_database():
    conn = get_connection()
    cur = conn.cursor()
    
    # Create tables if they don't exist
    with open('database/schema.sql', 'r') as f:
        sql = f.read()
        cur.execute(sql)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized successfully")

if __name__ == "__main__":
    init_database()
