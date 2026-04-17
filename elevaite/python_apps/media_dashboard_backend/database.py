# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import Tuple, List, Optional
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load .env file
load_dotenv()

def log_query(query, params=None):
    """Log SQL query and parameters"""
    if params:
        param_str = ", ".join(str(p) for p in params)
        logging.debug(f"Executing SQL: {query} with params: [{param_str}]")
    else:
        logging.debug(f"Executing SQL: {query}")

def get_db_connection():
    """Get a connection to the Media PostgreSQL database"""
    try:
        # Try to get media database connection string first
        database_url = os.getenv("MEDIA_DATABASE_URL")

        # Fallback to individual components if MEDIA_DATABASE_URL is not set
        if not database_url:
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_username = os.getenv("DB_USERNAME", "postgres")
            db_password = os.getenv("DB_PASSWORD", "")
            db_name = os.getenv("DB_NAME", "creative_db")

            database_url = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"

        if not database_url:
            raise ValueError("Media database connection parameters not set")

        # Log connection attempt (without exposing password)
        logging.info(f"Connecting to media database: {database_url.split('@')[-1]}")

        # Connect to the database
        conn = psycopg2.connect(database_url)

        # Set cursor to return dictionaries
        conn.cursor_factory = RealDictCursor

        # Log successful connection
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            db_info = cur.fetchone()
            logging.info(f"Connected to media database: {db_info['current_database']} as {db_info['current_user']}")

        return conn
    except Exception as e:
        logging.error(f"Media database connection error: {e}")
        raise

# Media database helper functions
def log_media_query(query, params=None):
    """Log media SQL queries for debugging"""
    if params:
        param_str = ", ".join(str(p) for p in params)
        logging.debug(f"[MEDIA] SQL: {query} | PARAMS: {param_str}")
    else:
        logging.debug(f"[MEDIA] SQL: {query}")

def build_session_date_filter(table_alias: str = "") -> callable:
    """
    Build a consistent date filter SQL clause for sessions

    Args:
        table_alias: Optional table alias (e.g., "s." for "s.creation_time")

    Returns:
        Function that takes start_date and end_date and returns filter and params
    """
    def get_filter(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[str, List]:
        prefix = f"{table_alias}." if table_alias else ""
        date_field = f"{prefix}creation_time"

        if start_date and end_date:
            return f"WHERE {date_field} BETWEEN %s AND %s", [start_date, end_date]
        elif start_date:
            return f"WHERE {date_field} >= %s", [start_date]
        elif end_date:
            return f"WHERE {date_field} <= %s", [end_date]
        else:
            return "", []

    return get_filter

def build_query_date_filter(table_alias: str = "") -> callable:
    """
    Build a consistent date filter SQL clause for queries

    Args:
        table_alias: Optional table alias (e.g., "q." for "q.start_time")

    Returns:
        Function that takes start_date and end_date and returns filter and params
    """
    def get_filter(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[str, List]:
        prefix = f"{table_alias}." if table_alias else ""
        date_field = f"{prefix}start_time"

        if start_date and end_date:
            return f"WHERE {date_field} BETWEEN %s AND %s", [start_date, end_date]
        elif start_date:
            return f"WHERE {date_field} >= %s", [start_date]
        elif end_date:
            return f"WHERE {date_field} <= %s", [end_date]
        else:
            return "", []

    return get_filter

# Media database date filtering
def build_media_date_filter(start_date: Optional[str] = None, end_date: Optional[str] = None, date_field: str = "creation_time") -> Tuple[str, List]:
    """
    Build date filter for media queries

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        date_field: The date field to filter on (default: creation_time)

    Returns:
        Tuple of (filter_clause, params_list)
    """
    date_filter = ""
    params = []

    if start_date and end_date:
        date_filter = f"WHERE {date_field} BETWEEN %s AND %s"
        params = [start_date, end_date]
    elif start_date:
        date_filter = f"WHERE {date_field} >= %s"
        params = [start_date]
    elif end_date:
        date_filter = f"WHERE {date_field} <= %s"
        params = [end_date]

    return date_filter, params

# Test media database connection
def test_media_connection():
    """Test if media tables are accessible"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Test all media tables
        tables = ['sessions', 'queries', 'agent_execution_steps', 'feedback', 'related_queries']
        table_counts = {}

        for table in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            table_counts[table] = count

        cur.close()
        conn.close()

        logging.info(f"✅ Media connection test successful:")
        for table, count in table_counts.items():
            logging.info(f"   - {table}: {count} records")

        return {
            "status": "success",
            **table_counts
        }

    except Exception as e:
        logging.error(f"❌ Media connection test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
def verify_all_tables():
    """Verify all required media tables exist"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check for media tables
        media_tables = ['sessions', 'queries', 'agent_execution_steps', 'feedback', 'related_queries']

        existing_tables = []
        missing_tables = []

        for table in media_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()['count']
                existing_tables.append(f"{table} ({count:,} records)")
            except psycopg2.Error:
                missing_tables.append(table)

        cur.close()
        conn.close()

        logging.info("📋 Media table verification complete:")
        for table in existing_tables:
            logging.info(f"   ✅ {table}")
        for table in missing_tables:
            logging.error(f"   ❌ {table} - NOT FOUND")

        return {
            "existing": existing_tables,
            "missing": missing_tables,
            "all_present": len(missing_tables) == 0
        }

    except Exception as e:
        logging.error(f"Media table verification failed: {e}")
        return {
            "existing": [],
            "missing": media_tables,
            "all_present": False,
            "error": str(e)
        }