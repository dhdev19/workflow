"""
Script to check database connection and list available databases.
Run this to find the correct database name.
"""
import os
from dotenv import load_dotenv
import pymysql
from urllib.parse import quote_plus

load_dotenv()

DB_HOSTNAME = os.getenv('DB_HOSTNAME', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

try:
    print(f"Connecting to {DB_HOSTNAME} as {DB_USER}...")
    connection = pymysql.connect(
        host=DB_HOSTNAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    print("✓ Connection successful!\n")
    print("Available databases:")
    print("-" * 50)
    
    with connection.cursor() as cursor:
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        for db in databases:
            db_name = db[0]
            # Filter out system databases
            if db_name not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                print(f"  - {db_name}")
        
        if not any(db[0] not in ['information_schema', 'performance_schema', 'mysql', 'sys'] for db in databases):
            print("  (No user databases found)")
    
    connection.close()
    print("\n" + "-" * 50)
    print("Update DB_NAME in your .env file with the correct database name.")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nPlease check:")
    print("1. DB_HOSTNAME, DB_USER, and DB_PASSWORD in .env file")
    print("2. Database server is accessible")
    print("3. User credentials are correct")

