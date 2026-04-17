#!/usr/bin/env python3
"""
Migration 005: Create Updated Insertion Order Tables

This migration creates the updated insertion order related tables with the new schema:

Tables created:
1. insertion_orders - Updated main insertion order data with workspace_type, creative_inspiration_id, io_pdf_id, media_plan_id
2. insertion_order_salesforce_mapping - Maps insertion orders to Salesforce IDs
3. insertion_order_google_drive_mapping - Maps insertion orders to Google Drive IDs
4. campaigns - Campaign data (structure unchanged but now maps to insertion orders via separate table)
5. campaign_insertion_order_mapping - Maps campaigns to insertion orders
6. placements - Updated to reference insertion orders directly instead of campaigns
7. status_changes - Status change tracking for insertion orders (unchanged)

Key Changes:
- Removed columns from insertion_orders: shell_created_at, in_flight_at, stopped_at, completed_at, pdf_file_id, sheet_id, drive_folder_id, approved_at
- Added columns to insertion_orders: workspace_type, creative_inspiration_id, io_pdf_id, media_plan_id
- Placements now reference insertion_order_id instead of campaign_id
- Added separate mapping tables for Salesforce and Google Drive integration
- Added campaign-to-insertion-order mapping table

This migration is idempotent and can be run multiple times safely.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USERNAME", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "creative_db")
    )

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s 
            AND column_name = %s
        );
    """, (table_name, column_name))
    return cursor.fetchone()[0]
def safe_add_column(cursor, table_name, column_name, column_definition):
    """Safely add a column if it doesn't exist"""
    if not check_column_exists(cursor, table_name, column_name):
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition};"
        cursor.execute(sql)
        logger.info(f"✅ Added column {column_name} to {table_name}")
        return True
    else:
        logger.info(f"⚠️  Column {column_name} already exists in {table_name}")
        return False
    
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

def create_insertion_orders_table(cursor):
    """Create updated insertion_orders table with new schema"""
    print("\n=== Creating insertion_orders table ===")

    if check_table_exists(cursor, 'insertion_orders'):
        print("✓ insertion_orders table already exists")
        return True

    sql = """
    CREATE TABLE insertion_orders (
        id VARCHAR(255) PRIMARY KEY,
        order_no VARCHAR(255) NOT NULL UNIQUE,
        brand VARCHAR(255),
        campaign_name VARCHAR(255) NOT NULL,
        customer_approver VARCHAR(255) NOT NULL,
        customer_approver_email VARCHAR(255) NOT NULL,
        sales_owner VARCHAR(255) NOT NULL,
        sales_owner_email VARCHAR(255) NOT NULL,
        fulfillment_owner VARCHAR(255) NOT NULL,
        fulfillment_owner_email VARCHAR(255) NOT NULL,
        objective_description TEXT,
        status VARCHAR(50) NOT NULL DEFAULT 'draft',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        workspace_type VARCHAR(50) CHECK (workspace_type IN ('google_drive', 'salesforce')),
        creative_inspiration_id VARCHAR(255),
        io_pdf_id VARCHAR(255),
        media_plan_id VARCHAR(255),
        raw_data JSONB DEFAULT '{}'::jsonb
    );

    -- Create indexes for insertion_orders
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_order_no ON insertion_orders(order_no);
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_status ON insertion_orders(status);
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_created_at ON insertion_orders(created_at);
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_campaign_name ON insertion_orders(campaign_name);
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_brand ON insertion_orders(brand);
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_workspace_type ON insertion_orders(workspace_type);
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_creative_inspiration_id ON insertion_orders(creative_inspiration_id);
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_creative_inspiration_id ON insertion_orders(creative_inspiration_id);
    CREATE INDEX IF NOT EXISTS idx_insertion_orders_creative_inspiration_id ON insertion_orders(creative_inspiration_id);
    """
    return execute_sql(cursor, sql, "Creating insertion_orders table and indexes")

def create_insertion_order_salesforce_mapping_table(cursor):
    """Create insertion_order_salesforce_mapping table"""
    print("\n=== Creating insertion_order_salesforce_mapping table ===")

    if check_table_exists(cursor, 'insertion_order_salesforce_mapping'):
        print("✓ insertion_order_salesforce_mapping table already exists")
        return True

    sql = """
    CREATE TABLE insertion_order_salesforce_mapping (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        insertion_order_id VARCHAR(255) NOT NULL,
        salesforce_io_id VARCHAR(255) NOT NULL,
        salesforce_account_id VARCHAR(255),
        salesforce_opportunity_id VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        FOREIGN KEY (insertion_order_id) REFERENCES insertion_orders(id) ON DELETE CASCADE
    );

    -- Create indexes for insertion_order_salesforce_mapping
    CREATE INDEX IF NOT EXISTS idx_io_salesforce_insertion_order_id ON insertion_order_salesforce_mapping(insertion_order_id);
    CREATE INDEX IF NOT EXISTS idx_io_salesforce_io_id ON insertion_order_salesforce_mapping(salesforce_io_id);
    CREATE INDEX IF NOT EXISTS idx_io_salesforce_account_id ON insertion_order_salesforce_mapping(salesforce_account_id);
    CREATE INDEX IF NOT EXISTS idx_io_salesforce_opportunity_id ON insertion_order_salesforce_mapping(salesforce_opportunity_id);
    """
    return execute_sql(cursor, sql, "Creating insertion_order_salesforce_mapping table and indexes")

def create_insertion_order_google_drive_mapping_table(cursor):
    """Create insertion_order_google_drive_mapping table"""
    print("\n=== Creating insertion_order_google_drive_mapping table ===")

    if check_table_exists(cursor, 'insertion_order_google_drive_mapping'):
        print("✓ insertion_order_google_drive_mapping table already exists")
        return True

    sql = """
    CREATE TABLE insertion_order_google_drive_mapping (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        insertion_order_id VARCHAR(255) NOT NULL,
        drive_folder_id VARCHAR(255),
        sheet_id VARCHAR(255),
        pdf_file_id VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        FOREIGN KEY (insertion_order_id) REFERENCES insertion_orders(id) ON DELETE CASCADE
    );

    -- Create indexes for insertion_order_google_drive_mapping
    CREATE INDEX IF NOT EXISTS idx_io_gdrive_insertion_order_id ON insertion_order_google_drive_mapping(insertion_order_id);
    CREATE INDEX IF NOT EXISTS idx_io_gdrive_folder_id ON insertion_order_google_drive_mapping(drive_folder_id);
    CREATE INDEX IF NOT EXISTS idx_io_gdrive_sheet_id ON insertion_order_google_drive_mapping(sheet_id);
    CREATE INDEX IF NOT EXISTS idx_io_gdrive_pdf_file_id ON insertion_order_google_drive_mapping(pdf_file_id);
    """
    return execute_sql(cursor, sql, "Creating insertion_order_google_drive_mapping table and indexes")

def create_campaigns_table(cursor):
    """Create campaigns table (simplified structure with placement data moved to campaign_placements)"""
    print("\n=== Creating campaigns table ===")

    if check_table_exists(cursor, 'campaigns'):
        print("✓ campaigns table already exists")
        return True

    sql = """
    CREATE TABLE campaigns (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        kevel_id VARCHAR(255) UNIQUE,
        status VARCHAR(50) NOT NULL DEFAULT 'shell_created',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );

    -- Create indexes for campaigns
    CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
    CREATE INDEX IF NOT EXISTS idx_campaigns_name ON campaigns(name);
    CREATE INDEX IF NOT EXISTS idx_campaigns_kevel_id ON campaigns(kevel_id);
    """
    return execute_sql(cursor, sql, "Creating campaigns table and indexes")

def create_campaign_daily_metrics_table(cursor):
    """Create table for daily campaign metrics; ensure revenue column exists."""
    print("\n=== Creating campaign_daily_metrics table ===")
    if check_table_exists(cursor, 'campaign_daily_metrics'):
        logger.info("campaign_daily_metrics table already exists")
        # Adding breakdown columns if they don't exist first (before adding unique constraint
        try:
            logger.info("Adding targeting_type column...")
            safe_add_column(cursor, 'campaign_daily_metrics', 'targeting_type', "TEXT DEFAULT ''")
            logger.info("Adding audience_segment column...")
            safe_add_column(cursor, 'campaign_daily_metrics', 'audience_segment', "TEXT DEFAULT ''")
            logger.info("Adding creative_type column...")
            safe_add_column(cursor, 'campaign_daily_metrics', 'creative_type', "TEXT DEFAULT ''")
            logger.info("Adding age_group column...")
            safe_add_column(cursor, 'campaign_daily_metrics', 'age_group', "TEXT DEFAULT ''")
            logger.info("Adding geo_location column...")
            safe_add_column(cursor, 'campaign_daily_metrics', 'geo_location', "TEXT DEFAULT ''")
        except Exception as e:
            logger.warning(f"Could not add columns to campaign_daily_metrics: {e}")
        # Drop old constraint 
        try:
            cursor.execute("""
                ALTER TABLE campaign_daily_metrics
                DROP CONSTRAINT IF EXISTS campaign_daily_metrics_campaign_id_metric_date_data_source_key;
            """)
            logger.info("Dropped old unique constraint")
        except Exception as e:
            logger.warning(f"Could not drop old unique constraint: {e}")

        # Added new unique constraint with all breakdown columns
        try:
            cursor.execute("""
                ALTER TABLE campaign_daily_metrics
                ADD CONSTRAINT campaign_daily_metrics_unique_breakdown
                UNIQUE (
                    campaign_id, metric_date, platform_channel, targeting_type,
                    audience_segment, creative_type, age_group, geo_location, data_source
                );
            """)
            logger.info("Added new unique constraint for breakdowns")
        except Exception as e:
            logger.warning(f"Could not add new unique constraint: {e}")
        return True

    sql = """
    CREATE TABLE campaign_daily_metrics (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
        metric_date DATE NOT NULL,
        platform_channel TEXT,
        targeting_type TEXT,
        audience_segment TEXT,
        creative_type TEXT,
        age_group TEXT,
        geo_location TEXT,
        data_source TEXT DEFAULT 'production',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(
            campaign_id, metric_date, platform_channel, targeting_type,
            audience_segment, creative_type, age_group, geo_location, data_source
        )
    );

    -- Helpful indexes
    CREATE INDEX IF NOT EXISTS idx_campaign_daily_metrics_campaign_date ON campaign_daily_metrics(campaign_id, metric_date);
    CREATE INDEX IF NOT EXISTS idx_campaign_daily_metrics_date ON campaign_daily_metrics(metric_date);

    COMMENT ON TABLE campaign_daily_metrics IS 'Per-day campaign performance metrics to support time series dashboards';
    COMMENT ON COLUMN campaign_daily_metrics.metric_date IS 'Date for the daily metrics row';
    """

    try:
        cursor.execute(sql)
        logger.info("Created campaign_daily_metrics table")
        return True
    except Exception as e:
        logger.error(f"Failed to create campaign_daily_metrics table: {e}")
        return False
    
def create_campaign_placements_table(cursor):
    """Create campaign_placements table with placement details for campaigns"""
    print("\n=== Creating campaign_placements table ===")

    if check_table_exists(cursor, 'campaign_placements'):
        print("✓ campaign_placements table already exists")
        return True
    #Adding revenue column to campaign placements table inorder to create revenue column in campaign table
    sql = """
    CREATE TABLE campaign_placements (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id UUID NOT NULL,
        flight_id VARCHAR(255),
        start_date DATE,
        end_date DATE,
        impressions_booked INTEGER DEFAULT 0,
        impressions_delivered INTEGER DEFAULT 0,
        booked_clicks INTEGER DEFAULT 0,
        delivered_clicks INTEGER DEFAULT 0,
        ctr NUMERIC(10, 6) DEFAULT 0.0,
        budget NUMERIC(15, 2) DEFAULT 0.0,
        revenue NUMERIC(15, 2) DEFAULT 0.0,
        cpm NUMERIC(10, 2) DEFAULT 0.0,
        cpc NUMERIC(10, 2) DEFAULT 0.0,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
    );

    -- Create indexes for campaign_placements
    CREATE INDEX IF NOT EXISTS idx_campaign_placements_campaign_id ON campaign_placements(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_campaign_placements_flight_id ON campaign_placements(flight_id);
    CREATE INDEX IF NOT EXISTS idx_campaign_placements_start_date ON campaign_placements(start_date);
    CREATE INDEX IF NOT EXISTS idx_campaign_placements_end_date ON campaign_placements(end_date);
    """
    return execute_sql(cursor, sql, "Creating campaign_placements table and indexes")

def create_campaign_insertion_order_mapping_table(cursor):
    """Create campaign_insertion_order_mapping table"""
    print("\n=== Creating campaign_insertion_order_mapping table ===")

    if check_table_exists(cursor, 'campaign_insertion_order_mapping'):
        print("✓ campaign_insertion_order_mapping table already exists")
        return True

    sql = """
    CREATE TABLE campaign_insertion_order_mapping (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id UUID NOT NULL,
        insertion_order_id VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
        FOREIGN KEY (insertion_order_id) REFERENCES insertion_orders(id) ON DELETE CASCADE,
        UNIQUE(campaign_id, insertion_order_id)
    );

    -- Create indexes for campaign_insertion_order_mapping
    CREATE INDEX IF NOT EXISTS idx_campaign_io_mapping_campaign_id ON campaign_insertion_order_mapping(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_campaign_io_mapping_insertion_order_id ON campaign_insertion_order_mapping(insertion_order_id);
    """
    return execute_sql(cursor, sql, "Creating campaign_insertion_order_mapping table and indexes")

def create_creative_assets_table(cursor):
    """Create creative_assets table"""
    print("\n=== Creating creative_assets table ===")

    if check_table_exists(cursor, 'creative_assets'):
        print("✓ creative_assets table already exists")
        return True

    sql = """
    CREATE TABLE creative_assets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        file_url TEXT,
        file_type VARCHAR(50),
        file_size BIGINT,
        width INTEGER,
        height INTEGER,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );

    -- Create indexes for creative_assets
    CREATE INDEX IF NOT EXISTS idx_creative_assets_name ON creative_assets(name);
    CREATE INDEX IF NOT EXISTS idx_creative_assets_file_type ON creative_assets(file_type);
    CREATE INDEX IF NOT EXISTS idx_creative_assets_created_at ON creative_assets(created_at);
    """
    return execute_sql(cursor, sql, "Creating creative_assets table and indexes")

def create_campaign_creative_mapping_table(cursor):
    """Create campaign_creative_mapping table"""
    print("\n=== Creating campaign_creative_mapping table ===")

    if check_table_exists(cursor, 'campaign_creative_mapping'):
        print("✓ campaign_creative_mapping table already exists")
        return True

    sql = """
    CREATE TABLE campaign_creative_mapping (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id UUID NOT NULL,
        creative_asset_id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
        FOREIGN KEY (creative_asset_id) REFERENCES creative_assets(id) ON DELETE CASCADE,
        UNIQUE(campaign_id, creative_asset_id)
    );

    -- Create indexes for campaign_creative_mapping
    CREATE INDEX IF NOT EXISTS idx_campaign_creative_mapping_campaign_id ON campaign_creative_mapping(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_campaign_creative_mapping_creative_asset_id ON campaign_creative_mapping(creative_asset_id);
    """
    return execute_sql(cursor, sql, "Creating campaign_creative_mapping table and indexes")

def create_placements_table(cursor):
    """Create placements table (now references insertion_order_id instead of campaign_id)"""
    print("\n=== Creating placements table ===")

    if check_table_exists(cursor, 'placements'):
        print("✓ placements table already exists")
        return True

    sql = """
    CREATE TABLE placements (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        insertion_order_id VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        destination VARCHAR(255),
        start_date DATE,
        end_date DATE,
        convert_to_campaign BOOLEAN DEFAULT FALSE,
        impressions_booked INTEGER DEFAULT 0,
        impressions_delivered INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        ctr NUMERIC(10, 6) DEFAULT 0.0,
        budget NUMERIC(15, 2) DEFAULT 0.0,
        cpm NUMERIC(10, 2) DEFAULT 0.0,
        cpc NUMERIC(10, 2) DEFAULT 0.0,
        targeting_config JSONB DEFAULT '{}'::jsonb,
        status VARCHAR(50) NOT NULL DEFAULT 'draft',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        FOREIGN KEY (insertion_order_id) REFERENCES insertion_orders(id) ON DELETE CASCADE
    );

    -- Create indexes for placements
    CREATE INDEX IF NOT EXISTS idx_placements_insertion_order_id ON placements(insertion_order_id);
    CREATE INDEX IF NOT EXISTS idx_placements_status ON placements(status);
    CREATE INDEX IF NOT EXISTS idx_placements_start_date ON placements(start_date);
    CREATE INDEX IF NOT EXISTS idx_placements_end_date ON placements(end_date);
    CREATE INDEX IF NOT EXISTS idx_placements_name ON placements(name);
    CREATE INDEX IF NOT EXISTS idx_placements_destination ON placements(destination);

    -- Add comment for convert_to_campaign column
    COMMENT ON COLUMN placements.convert_to_campaign IS
    'Flag indicating whether this placement should be converted into an individual campaign';
    """
    return execute_sql(cursor, sql, "Creating placements table and indexes")

def create_status_changes_table(cursor):
    """Create status_changes table"""
    print("\n=== Creating status_changes table ===")
    
    if check_table_exists(cursor, 'status_changes'):
        print("✓ status_changes table already exists")
        return True
    
    sql = """
    CREATE TABLE status_changes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        insertion_order_id VARCHAR(255) NOT NULL,
        previous_status VARCHAR(50),
        new_status VARCHAR(50) NOT NULL,
        changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        changed_by VARCHAR(255),
        reason TEXT,
        FOREIGN KEY (insertion_order_id) REFERENCES insertion_orders(id) ON DELETE CASCADE
    );

    -- Create indexes for status_changes
    CREATE INDEX IF NOT EXISTS idx_status_changes_insertion_order_id ON status_changes(insertion_order_id);
    CREATE INDEX IF NOT EXISTS idx_status_changes_changed_at ON status_changes(changed_at);
    CREATE INDEX IF NOT EXISTS idx_status_changes_new_status ON status_changes(new_status);
    CREATE INDEX IF NOT EXISTS idx_status_changes_changed_by ON status_changes(changed_by);
    """
    return execute_sql(cursor, sql, "Creating status_changes table and indexes")

def verify_tables(cursor):
    """Verify all tables were created successfully"""
    print("\n=== Verifying tables ===")

    required_tables = [
        'insertion_orders',
        'insertion_order_salesforce_mapping',
        'insertion_order_google_drive_mapping',
        'campaigns',
        'campaign_daily_metrics',
        'campaign_placements',
        'campaign_insertion_order_mapping',
        'creative_assets',
        'campaign_creative_mapping',
        'placements',
        'status_changes'
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
    print("Starting Migration 005: Create Updated Insertion Order Tables")
    print("=" * 70)

    try:
        # Connect to database
        conn = get_db_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print(f"Connected to database: {os.getenv('DB_NAME', 'creative_db')}")

        # Create tables in dependency order
        success = True
        success &= create_insertion_orders_table(cursor)
        success &= create_insertion_order_salesforce_mapping_table(cursor)
        success &= create_insertion_order_google_drive_mapping_table(cursor)
        success &= create_campaigns_table(cursor)
        success &= create_campaign_daily_metrics_table(cursor)
        success &= create_campaign_placements_table(cursor)
        success &= create_campaign_insertion_order_mapping_table(cursor)
        success &= create_creative_assets_table(cursor)
        success &= create_campaign_creative_mapping_table(cursor)
        success &= create_placements_table(cursor)
        success &= create_status_changes_table(cursor)

        # Verify all tables exist
        if success:
            success &= verify_tables(cursor)

        if success:
            print("\n" + "=" * 70)
            print("✓ Migration 005 completed successfully!")
            print("All updated insertion order tables have been created.")
            print("\nKey changes implemented:")
            print("- Updated insertion_orders table with new columns")
            print("- Added Salesforce and Google Drive mapping tables")
            print("- Updated placements to reference insertion_orders directly")
            print("- Added campaign-to-insertion-order mapping table")
            print("- Added creative_assets table and campaign-creative mapping")
        else:
            print("\n" + "=" * 70)
            print("✗ Migration 005 failed!")
            print("Some tables could not be created.")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Migration failed with error: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()