#!/usr/bin/env python3
"""
Migration 003: Create Media Backend Core Tables

This migration ensures all core media backend tables exist with the correct schema:
1. sessions - Session metadata and tracking
2. queries - Individual query execution data  
3. agent_execution_steps - Detailed agent execution tracking
4. feedback - User feedback and voting
5. related_queries - Related query suggestions storage

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
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "creative_db"),
        user=os.getenv("DB_USERNAME", "postgres"),
        password=os.getenv("DB_PASSWORD", "12345")
    )

def execute_sql(cursor, sql, description):
    """Execute SQL with error handling"""
    try:
        print(f"Executing: {description}")
        cursor.execute(sql)
        print(f"✓ {description} completed successfully")
        return True
    except Exception as e:
        print(f"✗ Error in {description}: {e}")
        return False

def check_table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_name = %s AND table_schema = 'public'
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def create_sessions_table(cursor):
    """Create sessions table"""
    print("\n=== Creating sessions table ===")
    
    if check_table_exists(cursor, 'sessions'):
        print("✓ sessions table already exists")
        return True
    
    sql = """
    CREATE TABLE sessions (
        session_id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        session_name VARCHAR(500) NOT NULL,
        creation_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        last_activity_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        total_queries INTEGER DEFAULT 0,
        session_summary TEXT,
        total_tokens_used JSONB DEFAULT '{}'::jsonb,
        feedback_count INTEGER DEFAULT 0,
        positive_feedback_count INTEGER DEFAULT 0,
        negative_feedback_count INTEGER DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_creation_time ON sessions(creation_time);
    CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity_time);
    """
    return execute_sql(cursor, sql, "Creating sessions table and indexes")

def create_queries_table(cursor):
    """Create queries table"""
    print("\n=== Creating queries table ===")
    
    if check_table_exists(cursor, 'queries'):
        print("✓ queries table already exists")
        return True
    
    sql = """
    CREATE TABLE queries (
        query_id VARCHAR(255) PRIMARY KEY,
        session_id VARCHAR(255) NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        original_query TEXT NOT NULL,
        start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        end_time TIMESTAMP WITH TIME ZONE,
        total_duration_ms INTEGER,
        final_response TEXT,
        intent_detected VARCHAR(100),
        agents_used JSONB DEFAULT '[]'::jsonb,
        total_tokens_used JSONB DEFAULT '{}'::jsonb,
        success BOOLEAN DEFAULT TRUE,
        error_details TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_queries_session_id ON queries(session_id);
    CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries(user_id);
    CREATE INDEX IF NOT EXISTS idx_queries_start_time ON queries(start_time);
    CREATE INDEX IF NOT EXISTS idx_queries_intent ON queries(intent_detected);
    """
    return execute_sql(cursor, sql, "Creating queries table and indexes")

def create_agent_execution_steps_table(cursor):
    """Create agent_execution_steps table"""
    print("\n=== Creating agent_execution_steps table ===")
    
    if check_table_exists(cursor, 'agent_execution_steps'):
        print("✓ agent_execution_steps table already exists")
        return True
    
    sql = """
    CREATE TABLE agent_execution_steps (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        query_id VARCHAR(255) NOT NULL,
        agent_name VARCHAR(100) NOT NULL,
        step_type VARCHAR(100) NOT NULL,
        start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        end_time TIMESTAMP WITH TIME ZONE,
        duration_ms INTEGER,
        input_prompt TEXT,
        output_response TEXT,
        model_used VARCHAR(100),
        tokens_used JSONB DEFAULT '{}'::jsonb,
        success BOOLEAN DEFAULT TRUE,
        error_details TEXT,
        step_metadata JSONB DEFAULT '{}'::jsonb,
        FOREIGN KEY (query_id) REFERENCES queries(query_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_agent_steps_query_id ON agent_execution_steps(query_id);
    CREATE INDEX IF NOT EXISTS idx_agent_steps_agent_name ON agent_execution_steps(agent_name);
    CREATE INDEX IF NOT EXISTS idx_agent_steps_start_time ON agent_execution_steps(start_time);
    CREATE INDEX IF NOT EXISTS idx_agent_steps_step_type ON agent_execution_steps(step_type);
    """
    return execute_sql(cursor, sql, "Creating agent_execution_steps table and indexes")

def create_feedback_table(cursor):
    """Create feedback table"""
    print("\n=== Creating feedback table ===")
    
    if check_table_exists(cursor, 'feedback'):
        print("✓ feedback table already exists")
        return True
    
    sql = """
    CREATE TABLE feedback (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        query_id VARCHAR(255) NOT NULL,
        session_id VARCHAR(255) NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        feedback_type VARCHAR(50) NOT NULL,
        feedback_text TEXT,
        vote INTEGER DEFAULT 0,
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        FOREIGN KEY (query_id) REFERENCES queries(query_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_feedback_query_id ON feedback(query_id);
    CREATE INDEX IF NOT EXISTS idx_feedback_session_id ON feedback(session_id);
    CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
    CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp);
    CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type);
    """
    return execute_sql(cursor, sql, "Creating feedback table and indexes")

def create_related_queries_table(cursor):
    """Create related_queries table"""
    print("\n=== Creating related_queries table ===")
    
    if check_table_exists(cursor, 'related_queries'):
        print("✓ related_queries table already exists")
        return True
    
    sql = """
    CREATE TABLE related_queries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        query_id VARCHAR(255) NOT NULL,
        session_id VARCHAR(255) NOT NULL,
        related_queries JSONB DEFAULT '[]'::jsonb,
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        FOREIGN KEY (query_id) REFERENCES queries(query_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_related_queries_query_id ON related_queries(query_id);
    CREATE INDEX IF NOT EXISTS idx_related_queries_session_id ON related_queries(session_id);
    CREATE INDEX IF NOT EXISTS idx_related_queries_timestamp ON related_queries(timestamp);
    """
    return execute_sql(cursor, sql, "Creating related_queries table and indexes")

def verify_tables(cursor):
    """Verify all tables were created successfully"""
    print("\n=== Verifying tables ===")
    
    required_tables = [
        'sessions', 'queries', 'agent_execution_steps', 
        'feedback', 'related_queries'
    ]
    
    all_exist = True
    for table in required_tables:
        if check_table_exists(cursor, table):
            print(f"✓ {table} table exists")
        else:
            print(f"✗ {table} table missing")
            all_exist = False
    
    return all_exist

def main():
    """Main migration function"""
    print("Starting Migration 003: Create Media Backend Core Tables")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = get_db_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print(f"Connected to database: {os.getenv('DB_NAME', 'creative_db')}")
        
        # Create tables in dependency order
        success = True
        success &= create_sessions_table(cursor)
        success &= create_queries_table(cursor)
        success &= create_agent_execution_steps_table(cursor)
        success &= create_feedback_table(cursor)
        success &= create_related_queries_table(cursor)
        
        # Verify all tables exist
        if verify_tables(cursor):
            print("\n" + "=" * 60)
            print("✓ Migration 003 completed successfully!")
            print("\nCore tables created/verified:")
            print("  - sessions")
            print("  - queries")
            print("  - agent_execution_steps")
            print("  - feedback")
            print("  - related_queries")
            print("\nAll tables are ready for use.")
        else:
            print("\n" + "=" * 60)
            print("✗ Migration 003 completed with errors")
            print("Some tables were not created successfully.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Migration failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
