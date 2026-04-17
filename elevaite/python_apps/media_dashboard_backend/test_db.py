#!/usr/bin/env python3
"""
Simple database connection test for media dashboard
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Get database credentials
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_username = os.getenv("DB_USERNAME", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "creative_db")
        
        print(f"Testing connection to: {db_host}:{db_port}/{db_name}")
        print(f"Username: {db_username}")
        
        # Create connection string
        connection_string = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Connect to database
        conn = psycopg2.connect(connection_string)
        conn.cursor_factory = RealDictCursor
        
        # Test query
        cur = conn.cursor()
        cur.execute("SELECT current_database(), current_user")
        result = cur.fetchone()
        
        print(f"✅ Connected successfully!")
        print(f"Database: {result['current_database']}")
        print(f"User: {result['current_user']}")
        
        # Test table counts
        tables = ['sessions', 'queries', 'agent_execution_steps', 'feedback', 'related_queries']
        print("\nTable counts:")
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cur.fetchone()['count']
                print(f"  {table}: {count:,} records")
            except Exception as e:
                print(f"  {table}: ERROR - {e}")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("Media Dashboard Database Connection Test")
    print("=" * 50)
    
    success = test_database_connection()
    
    if success:
        print("\n✅ Database test passed!")
        sys.exit(0)
    else:
        print("\n❌ Database test failed!")
        sys.exit(1)
