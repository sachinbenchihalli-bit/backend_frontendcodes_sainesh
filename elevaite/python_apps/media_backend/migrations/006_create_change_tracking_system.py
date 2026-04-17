#!/usr/bin/env python3
"""
Migration 006: Create Campaign Change Tracking System

This migration creates the infrastructure needed for tracking campaign changes:

1. Adds targeting columns to campaign_daily_metrics table:
   - targeting_type, audience_segment, age_group, geo_location

2. Creates campaign_change_tracking table for monitoring:
   - Targeting changes (targeting_type, audience_segment, age_group, geo_location)
   - Budget and spend changes (>7% variance)
   - Creative swaps (creative_url, creative_type changes)


3. Updates daily views to include creative information

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

def execute_sql(cursor, sql, description):
    """Execute SQL with error handling and logging"""
    try:
        cursor.execute(sql)
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}: {e}")
        return False

def add_targeting_columns_to_daily_metrics(cursor):
    """Add targeting columns to campaign_daily_metrics table"""
    print("\n=== Adding targeting columns to campaign_daily_metrics ===")
    
    # Check if campaign_daily_metrics table exists
    if not check_table_exists(cursor, 'campaign_daily_metrics'):
        print("⚠️  campaign_daily_metrics table does not exist. Skipping targeting columns.")
        return True
    
    targeting_columns = [
        ('targeting_type', 'VARCHAR(100)'),
        ('audience_segment', 'VARCHAR(255)'),
        ('age_group', 'VARCHAR(100)'),
        ('geo_location', 'VARCHAR(255)')
    ]
    
    success = True
    for column_name, column_type in targeting_columns:
        if not check_column_exists(cursor, 'campaign_daily_metrics', column_name):
            sql = f"ALTER TABLE campaign_daily_metrics ADD COLUMN {column_name} {column_type};"
            success &= execute_sql(cursor, sql, f"Adding {column_name} column to campaign_daily_metrics")
        else:
            print(f"✓ {column_name} column already exists in campaign_daily_metrics")
    
    # Add indexes for the new columns
    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_campaign_daily_metrics_targeting_type ON campaign_daily_metrics(targeting_type);
    CREATE INDEX IF NOT EXISTS idx_campaign_daily_metrics_audience_segment ON campaign_daily_metrics(audience_segment);
    CREATE INDEX IF NOT EXISTS idx_campaign_daily_metrics_age_group ON campaign_daily_metrics(age_group);
    CREATE INDEX IF NOT EXISTS idx_campaign_daily_metrics_geo_location ON campaign_daily_metrics(geo_location);
    """
    success &= execute_sql(cursor, index_sql, "Creating indexes for targeting columns")
    
    return success

def create_campaign_change_tracking_table(cursor):
    """Create campaign_change_tracking table"""
    print("\n=== Creating campaign_change_tracking table ===")

    if check_table_exists(cursor, 'campaign_change_tracking'):
        print("✓ campaign_change_tracking table already exists")
        return True

    sql = """
    CREATE TABLE campaign_change_tracking (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        campaign_id UUID NOT NULL,
        change_date DATE NOT NULL,
        change_type VARCHAR(50) NOT NULL CHECK (change_type IN ('targeting', 'budget_spend', 'creative')),
        previous_values JSONB DEFAULT '{}'::jsonb,
        new_values JSONB DEFAULT '{}'::jsonb,
        change_description TEXT,
        variance_percentage NUMERIC(10, 2),
        detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        data_source VARCHAR(50) DEFAULT 'system',
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
    );

    -- Create indexes for campaign_change_tracking
    CREATE INDEX IF NOT EXISTS idx_campaign_change_tracking_campaign_id ON campaign_change_tracking(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_campaign_change_tracking_change_date ON campaign_change_tracking(change_date);
    CREATE INDEX IF NOT EXISTS idx_campaign_change_tracking_change_type ON campaign_change_tracking(change_type);
    CREATE INDEX IF NOT EXISTS idx_campaign_change_tracking_detected_at ON campaign_change_tracking(detected_at);
    CREATE INDEX IF NOT EXISTS idx_campaign_change_tracking_variance ON campaign_change_tracking(variance_percentage);
    
    -- Add comments for documentation
    COMMENT ON TABLE campaign_change_tracking IS 'Tracks changes to campaigns including targeting, budget/spend, and creative modifications';
    COMMENT ON COLUMN campaign_change_tracking.change_type IS 'Type of change: targeting, budget_spend, or creative';
    COMMENT ON COLUMN campaign_change_tracking.previous_values IS 'JSON object containing previous field values';
    COMMENT ON COLUMN campaign_change_tracking.new_values IS 'JSON object containing new field values';
    COMMENT ON COLUMN campaign_change_tracking.variance_percentage IS 'Percentage change for budget/spend modifications';
    """
    return execute_sql(cursor, sql, "Creating campaign_change_tracking table and indexes")

def update_daily_view_with_creative_info(cursor):
    """Update dashboard_campaigns_daily_view to include creative information"""
    print("\n=== Updating daily view to include creative information ===")
    
    # Check if the view exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.views
            WHERE table_schema = 'public'
            AND table_name = 'dashboard_campaigns_daily_view'
        );
    """)
    
    if not cursor.fetchone()[0]:
        print("⚠️  dashboard_campaigns_daily_view does not exist. Skipping view update.")
        return True
    
    sql = """
    CREATE OR REPLACE VIEW dashboard_campaigns_daily_view AS
    SELECT
        cdm.id::text as id,
        c.id::text as campaign_id,
        cio.insertion_order_id::text as insertion_order_id,
        COALESCE(io.campaign_name, c.name) as name,
        COALESCE(c.brand, io.brand) as brand,
        c.kevel_id,
        c.platform_channel,
        cdm.metric_date::text as metric_date,
        cdm.impressions_booked,
        cdm.impressions_delivered,
        cdm.clicks,
        CASE
            WHEN cdm.impressions_delivered > 0 THEN
                (cdm.clicks::decimal / NULLIF(cdm.impressions_delivered, 0)) * 100
            ELSE COALESCE(cdm.ctr, 0.0)
        END as ctr,
        cdm.conversions,
        cdm.roas,
        cdm.spend,
        cdm.cpm,
        cdm.cpc,
        cdm.data_source,
        c.status,
        c.created_at::text,
        c.updated_at::text,
        
        -- Targeting information (new columns)
        cdm.targeting_type,
        cdm.audience_segment,
        cdm.age_group,
        cdm.geo_location,
        
        -- Creative information (joined from creative assets)
        ca.file_url as creative_url,
        ca.file_type as creative_type,
        ca.name as creative_name
        
    FROM campaign_daily_metrics cdm
    JOIN campaigns c ON cdm.campaign_id = c.id
    LEFT JOIN campaign_insertion_order_mapping cio ON c.id = cio.campaign_id
    LEFT JOIN insertion_orders io ON cio.insertion_order_id = io.id
    LEFT JOIN campaign_creative_mapping ccm ON c.id = ccm.campaign_id
    LEFT JOIN creative_assets ca ON ccm.creative_asset_id = ca.id
    ORDER BY cdm.metric_date DESC, c.created_at DESC;
    
    -- Add comment for documentation
    COMMENT ON VIEW dashboard_campaigns_daily_view IS 'Enhanced daily dashboard view including targeting and creative information for change tracking';
    """
    return execute_sql(cursor, sql, "Updating dashboard_campaigns_daily_view with creative and targeting info")

def verify_change_tracking_system(cursor):
    """Verify the change tracking system was created successfully"""
    print("\n=== Verifying change tracking system ===")
    
    # Check table exists
    if not check_table_exists(cursor, 'campaign_change_tracking'):
        print("✗ campaign_change_tracking table missing")
        return False
    
    print("✓ campaign_change_tracking table exists")
    
    # Check targeting columns in campaign_daily_metrics (if table exists)
    if check_table_exists(cursor, 'campaign_daily_metrics'):
        targeting_columns = ['targeting_type', 'audience_segment', 'age_group', 'geo_location']
        for column in targeting_columns:
            if check_column_exists(cursor, 'campaign_daily_metrics', column):
                print(f"✓ {column} column exists in campaign_daily_metrics")
            else:
                print(f"✗ {column} column missing from campaign_daily_metrics")
                return False
    
    # Check view exists and has new columns
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'dashboard_campaigns_daily_view'
        AND column_name IN ('targeting_type', 'creative_url', 'creative_type');
    """)
    
    view_columns = [row[0] for row in cursor.fetchall()]
    expected_columns = ['targeting_type', 'creative_url', 'creative_type']
    
    for column in expected_columns:
        if column in view_columns:
            print(f"✓ {column} column exists in dashboard_campaigns_daily_view")
        else:
            print(f"⚠️  {column} column missing from dashboard_campaigns_daily_view (may be expected if base tables don't exist)")
    
    return True

def main():
    """Main migration function"""
    print("Starting Migration 006: Create Campaign Change Tracking System")
    print("=" * 70)

    try:
        # Connect to database
        conn = get_db_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print(f"Connected to database: {os.getenv('DB_NAME', 'creative_db')}")

        # Execute migration steps
        success = True
        success &= add_targeting_columns_to_daily_metrics(cursor)
        success &= create_campaign_change_tracking_table(cursor)
        success &= update_daily_view_with_creative_info(cursor)

        # Verify the system
        if success:
            success &= verify_change_tracking_system(cursor)

        if success:
            print("\n" + "=" * 70)
            print("✓ Migration 006 completed successfully!")
            print("Campaign change tracking system is now ready:")
            print("  - Added targeting columns to campaign_daily_metrics")
            print("  - Created campaign_change_tracking table")
            print("  - Enhanced daily view with creative information")
            print("  - Ready to track targeting, budget/spend, and creative changes")
        else:
            print("\n" + "=" * 70)
            print("✗ Migration 006 completed with warnings!")
            print("Some components may not be available if base tables don't exist.")
            print("This is expected in environments without the adopt backend schema.")

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
