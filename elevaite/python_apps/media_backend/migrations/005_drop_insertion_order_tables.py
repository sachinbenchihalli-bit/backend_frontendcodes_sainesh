#!/usr/bin/env python3
"""
Migration 005 Cleanup: Drop Insertion Order Tables

This script drops all insertion order related tables to allow for a clean recreation
with the new schema structure.

Tables to be dropped:
1. status_changes (depends on insertion_orders)
2. placements (depends on insertion_orders)
3. campaign_creative_mapping (depends on campaigns and creative_assets)
4. campaign_insertion_order_mapping (depends on campaigns and insertion_orders)
5. campaigns (main table)
6. creative_assets (main table)
7. insertion_order_salesforce_mapping (depends on insertion_orders)
8. insertion_order_google_drive_mapping (depends on insertion_orders)
9. insertion_orders (main table)

WARNING: This will permanently delete all data in these tables!
Make sure you have a backup before running this script.

This script is idempotent and can be run multiple times safely.
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

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def execute_sql(cursor, sql, description):
    """Execute SQL with error handling and logging"""
    try:
        cursor.execute(sql)
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}: {e}")
        return False

def drop_table_if_exists(cursor, table_name):
    """Drop a table if it exists"""
    if check_table_exists(cursor, table_name):
        sql = f"DROP TABLE IF EXISTS {table_name} CASCADE;"
        return execute_sql(cursor, sql, f"Dropped table: {table_name}")
    else:
        print(f"✓ Table {table_name} does not exist (already dropped)")
        return True

def drop_all_insertion_order_tables(cursor):
    """Drop all insertion order related tables in correct dependency order"""
    print("\n=== Dropping insertion order related tables ===")
    
    # Tables to drop in dependency order (dependent tables first)
    tables_to_drop = [
        'status_changes',
        'placements',
        'campaign_creative_mapping',
        'campaign_placements',
        'campaign_insertion_order_mapping',
        'insertion_order_salesforce_mapping',
        'insertion_order_google_drive_mapping',
        'campaigns',
        'creative_assets',
        'insertion_orders'
    ]
    
    success = True
    for table in tables_to_drop:
        success &= drop_table_if_exists(cursor, table)
    
    return success

def verify_tables_dropped(cursor):
    """Verify all tables were dropped successfully"""
    print("\n=== Verifying tables are dropped ===")
    
    tables_to_check = [
        'insertion_orders',
        'insertion_order_salesforce_mapping',
        'insertion_order_google_drive_mapping',
        'campaigns',
        'campaign_placements',
        'campaign_insertion_order_mapping',
        'creative_assets',
        'campaign_creative_mapping',
        'placements',
        'status_changes'
    ]
    
    all_dropped = True
    for table in tables_to_check:
        if check_table_exists(cursor, table):
            print(f"✗ {table} table still exists")
            all_dropped = False
        else:
            print(f"✓ {table} table successfully dropped")
    
    return all_dropped

def main():
    """Main cleanup function"""
    print("Starting Migration 005 Cleanup: Drop Insertion Order Tables")
    print("=" * 70)
    print("⚠️  WARNING: This will permanently delete all data in insertion order tables!")
    print("⚠️  Make sure you have a backup before proceeding!")
    print("=" * 70)
    
    # Ask for confirmation
    response = input("\nDo you want to continue? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        print("Operation cancelled by user.")
        sys.exit(0)
    
    try:
        # Connect to database
        conn = get_db_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print(f"\nConnected to database: {os.getenv('DB_NAME', 'creative_db')}")
        
        # Drop all tables
        success = drop_all_insertion_order_tables(cursor)
        
        # Verify all tables are dropped
        if success:
            success &= verify_tables_dropped(cursor)
        
        if success:
            print("\n" + "=" * 70)
            print("✓ Migration 005 cleanup completed successfully!")
            print("All insertion order tables have been dropped.")
            print("You can now run the creation script to set up the new schema.")
        else:
            print("\n" + "=" * 70)
            print("✗ Migration 005 cleanup failed!")
            print("Some tables could not be dropped.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Cleanup failed with error: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
