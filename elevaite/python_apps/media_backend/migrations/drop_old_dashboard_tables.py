#!/usr/bin/env python3
"""
Drop Old Dashboard Tables Script

This script drops all old dashboard-related tables that are no longer needed
after migrating to the new media backend schema structure.

Tables to be dropped:
1. Dashboard Tables:
   - dashboard_campaigns
   - dashboard_creatives
   - dashboard_insertion_orders
   - dashboard_todo_items

2. Analytics/Metrics Tables:
   - campaign_weekly_stats
   - insertion_order_weekly_stats
   - campaign_success_metrics
   - campaign_performance_snapshots
   - campaign_next_actions
   - campaign_health_metrics

Note: The following tables and views will be PRESERVED:
   - campaign_data_table (legacy data table - kept)
   - creative_data_table (legacy data table - kept)
   - campaign_creatives (legacy table - kept)
   - campaign_dashboard_view (view - kept)
   - creative_dashboard_view (view - kept)

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

def check_view_exists(cursor, view_name):
    """Check if a view exists in the database"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (view_name,))
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

def drop_view_if_exists(cursor, view_name):
    """Drop a view if it exists"""
    if check_view_exists(cursor, view_name):
        sql = f"DROP VIEW IF EXISTS {view_name} CASCADE;"
        return execute_sql(cursor, sql, f"Dropped view: {view_name}")
    else:
        print(f"✓ View {view_name} does not exist (already dropped)")
        return True

def drop_all_dashboard_tables(cursor):
    """Drop dashboard related tables (excluding preserved legacy tables and views)"""
    print("\n=== Skipping views (preserved) ===")
    print("✓ campaign_dashboard_view - PRESERVED")
    print("✓ creative_dashboard_view - PRESERVED")

    success = True
    
    print("\n=== Dropping dashboard tables ===")

    # Tables to drop in dependency order (dependent tables first)
    tables_to_drop = [
        # Analytics and metrics tables (no dependencies)
        'campaign_weekly_stats',
        'insertion_order_weekly_stats',
        'campaign_success_metrics',
        'campaign_performance_snapshots',
        'campaign_next_actions',
        'campaign_health_metrics',
        'dashboard_todo_items',

        # Tables with foreign key dependencies
        'dashboard_creatives',        # depends on dashboard_campaigns
        'dashboard_campaigns',        # depends on dashboard_insertion_orders

        # Main dashboard tables
        'dashboard_insertion_orders'
    ]

    # Preserved tables (will not be dropped)
    preserved_tables = [
        'campaign_data_table',
        'creative_data_table',
        'campaign_creatives'
    ]

    print(f"\n=== Preserving legacy tables ===")
    for table in preserved_tables:
        print(f"✓ {table} - PRESERVED")
    
    for table in tables_to_drop:
        success &= drop_table_if_exists(cursor, table)
    
    return success

def verify_tables_dropped(cursor):
    """Verify dashboard tables were dropped and preserved tables still exist"""
    print("\n=== Verifying dashboard tables are dropped ===")

    tables_to_check_dropped = [
        'dashboard_campaigns',
        'dashboard_creatives',
        'dashboard_insertion_orders',
        'dashboard_todo_items',
        'campaign_weekly_stats',
        'insertion_order_weekly_stats',
        'campaign_success_metrics',
        'campaign_performance_snapshots',
        'campaign_next_actions',
        'campaign_health_metrics'
    ]

    tables_to_check_preserved = [
        'campaign_data_table',
        'creative_data_table',
        'campaign_creatives'
    ]

    views_to_check_preserved = [
        'campaign_dashboard_view',
        'creative_dashboard_view'
    ]

    all_correct = True

    # Check tables that should be dropped
    for table in tables_to_check_dropped:
        if check_table_exists(cursor, table):
            print(f"✗ {table} table still exists (should be dropped)")
            all_correct = False
        else:
            print(f"✓ {table} table successfully dropped")

    print("\n=== Verifying preserved tables still exist ===")
    # Check tables that should be preserved
    for table in tables_to_check_preserved:
        if check_table_exists(cursor, table):
            print(f"✓ {table} table preserved (still exists)")
        else:
            print(f"⚠️  {table} table missing (should be preserved)")
            # Don't mark as failure since it might not have existed

    print("\n=== Verifying preserved views still exist ===")
    # Check views that should be preserved
    for view in views_to_check_preserved:
        if check_view_exists(cursor, view):
            print(f"✓ {view} view preserved (still exists)")
        else:
            print(f"⚠️  {view} view missing (should be preserved)")
            # Don't mark as failure since it might not have existed

    return all_correct

def main():
    """Main cleanup function"""
    print("Starting Cleanup: Drop Old Dashboard Tables")
    print("=" * 60)
    print("⚠️  WARNING: This will permanently delete all data in dashboard tables!")
    print("⚠️  Make sure you have a backup before proceeding!")
    print("=" * 60)
    
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
        
        # Drop all dashboard tables and views
        success = drop_all_dashboard_tables(cursor)
        
        # Verify all tables and views are dropped
        if success:
            success &= verify_tables_dropped(cursor)
        
        if success:
            print("\n" + "=" * 60)
            print("✓ Dashboard cleanup completed successfully!")
            print("Old dashboard tables have been dropped.")
            print("Legacy tables and views have been preserved.")
            print("The database is now ready for the new media backend schema.")
        else:
            print("\n" + "=" * 60)
            print("✗ Dashboard cleanup failed!")
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
