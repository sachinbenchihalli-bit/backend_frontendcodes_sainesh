#!/usr/bin/env python3
"""
Migration 004: Create Targeting Configurations Table

This migration creates the targeting_configurations table for storing
user-defined targeting configurations that can be reused across placements.

This migration is idempotent and can be run multiple times safely.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USERNAME", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "creative_db")
    )

def create_targeting_configurations_table():
    """Create the targeting_configurations table"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS targeting_configurations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        targeting_config JSONB NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    """
    
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_targeting_configurations_user_id ON targeting_configurations(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_targeting_configurations_created_at ON targeting_configurations(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_targeting_configurations_name ON targeting_configurations(name);"
    ]
    
    conn = None
    try:
        conn = get_db_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Creating targeting_configurations table...")
        cursor.execute(create_table_sql)
        print("✓ targeting_configurations table created successfully")
        
        print("Creating indexes...")
        for index_sql in create_indexes_sql:
            cursor.execute(index_sql)
        print("✓ Indexes created successfully")
        
        cursor.close()
        
    except Exception as e:
        print(f"Error creating targeting_configurations table: {e}")
        raise
    finally:
        if conn:
            conn.close()

def verify_table_creation():
    """Verify that the table was created successfully"""
    
    verify_sql = """
    SELECT 
        column_name, 
        data_type, 
        is_nullable,
        column_default
    FROM information_schema.columns 
    WHERE table_name = 'targeting_configurations'
    ORDER BY ordinal_position;
    """
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(verify_sql)
        columns = cursor.fetchall()
        
        if columns:
            print("\n✓ targeting_configurations table structure:")
            for column in columns:
                print(f"  - {column[0]}: {column[1]} (nullable: {column[2]}, default: {column[3]})")
        else:
            print("✗ targeting_configurations table not found")
            
        cursor.close()
        
    except Exception as e:
        print(f"Error verifying table creation: {e}")
        raise
    finally:
        if conn:
            conn.close()

def main():
    """Main migration function"""
    print("Starting Migration 004: Create Targeting Configurations Table")
    print("=" * 60)
    
    try:
        create_targeting_configurations_table()
        verify_table_creation()
        
        print("\n" + "=" * 60)
        print("✓ Migration 004 completed successfully!")
        print("The targeting_configurations table is now ready for use.")
        
    except Exception as e:
        print(f"\n✗ Migration 004 failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
