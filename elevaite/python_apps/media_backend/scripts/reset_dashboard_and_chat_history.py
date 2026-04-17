#!/usr/bin/env python3
"""
Reset Dashboard and Chat History Script

This script resets all adopt dashboard tables and media chat history tables
while preserving:
- Toshiba backend tables (chat_data_final, agent_flow_data)
- Media analytics tables (campaign_data_table, creative_data_table)
- Database views and schemas

DANGER: This will permanently delete ALL data in the specified tables!
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get database connection using environment variables"""
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", 5432),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD")
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

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

def get_table_row_count(cursor, table_name):
    """Get the number of rows in a table"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        return cursor.fetchone()[0]
    except Exception:
        return 0

def truncate_table(cursor, table_name):
    """Truncate a table (delete all data but keep structure)"""
    try:
        if check_table_exists(cursor, table_name):
            row_count = get_table_row_count(cursor, table_name)
            if row_count > 0:
                cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;")
                logger.info(f"✓ Truncated {table_name} ({row_count} rows deleted)")
                return True
            else:
                logger.info(f"✓ {table_name} already empty")
                return True
        else:
            logger.warning(f"⚠ Table {table_name} does not exist, skipping")
            return False
    except Exception as e:
        logger.error(f"✗ Failed to truncate {table_name}: {e}")
        return False

def reset_tables():
    """Reset all specified tables"""
    
    # Tables to reset in dependency order (dependent tables first)
    tables_to_reset = [
        # Adopt Dashboard Tables (dependent tables first)
        'campaign_placements',              # depends on campaigns
        'campaign_insertion_order_mapping', # depends on campaigns and insertion_orders
        'status_changes',                   # depends on insertion_orders
        'placements',                       # depends on insertion_orders
        'campaigns',                        # main campaign table
        'insertion_orders',                 # main insertion order table
        'dashboard_todo_items',             # standalone
        'campaign_success_metrics',         # standalone
        'campaign_weekly_stats',            # standalone
        'insertion_order_weekly_stats',     # standalone
        
        # Media Backend Chat History Tables (dependent tables first)
        'agent_execution_steps',            # depends on queries
        'feedback',                         # depends on queries and sessions
        'related_queries',                  # depends on queries and sessions
        'queries',                          # depends on sessions
        'sessions',                         # main session table
    ]
    

    
    logger.info("=" * 60)
    logger.info("DASHBOARD AND CHAT HISTORY RESET SCRIPT")
    logger.info("=" * 60)
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Tables to reset: {len(tables_to_reset)}")
    logger.info("")

    # Get database connection
    connection = get_database_connection()
    cursor = connection.cursor()

    try:
        # Confirm before proceeding
        logger.warning("⚠️  WARNING: This will permanently delete ALL data in the following tables:")
        for table in tables_to_reset:
            if check_table_exists(cursor, table):
                row_count = get_table_row_count(cursor, table)
                logger.warning(f"   {table}: {row_count} rows will be DELETED")
        
        logger.info("")
        response = input("Are you sure you want to proceed? Type 'YES' to continue: ")
        if response != 'YES':
            logger.info("Operation cancelled by user")
            return
        
        logger.info("")
        logger.info("🗑️  Starting table reset...")
        
        # Reset tables
        success_count = 0
        for table in tables_to_reset:
            if truncate_table(cursor, table):
                success_count += 1
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("RESET COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Successfully reset: {success_count}/{len(tables_to_reset)} tables")
        logger.info("")
        logger.info("✅ Dashboard and chat history data has been reset!")
        logger.info("✅ All table structures and views are preserved")
        
    except Exception as e:
        logger.error(f"Error during reset: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    reset_tables()
