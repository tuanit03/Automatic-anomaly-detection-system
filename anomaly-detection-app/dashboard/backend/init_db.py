import asyncio
import logging
import psycopg2
from sqlalchemy import create_engine, text

import config
from database import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize database tables and TimescaleDB hypertables"""
    logger.info("Initializing database...")
    
    # Create all tables using SQLAlchemy
    engine = create_engine(config.DB_URL)
    Base.metadata.create_all(engine)
    logger.info("Created standard tables")
    
    # Connect directly using psycopg2 to execute TimescaleDB-specific commands
    try:
        conn = psycopg2.connect(
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Enable TimescaleDB extension if not already enabled
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        logger.info("TimescaleDB extension enabled")
        
        # Convert classifications table to hypertable
        cur.execute("""
            SELECT create_hypertable('classifications', 'timestamp', 
                                    if_not_exists => TRUE,
                                    migrate_data => TRUE);
        """)
        logger.info("Converted classifications to hypertable")
        
        # Set retention policy to 30 days (optional)
        cur.execute("""
            SELECT add_retention_policy('classifications', INTERVAL '30 days', if_not_exists => TRUE);
        """)
        logger.info("Added retention policy to classifications hypertable")
        
        # Convert anomaly_params table to hypertable
        cur.execute("""
            SELECT create_hypertable('anomaly_params', 'timestamp', 
                                    if_not_exists => TRUE,
                                    migrate_data => TRUE);
        """)
        logger.info("Converted anomaly_params to hypertable")
        
        # Convert log_entries table to hypertable
        cur.execute("""
            SELECT create_hypertable('log_entries', 'timestamp', 
                                    if_not_exists => TRUE,
                                    migrate_data => TRUE);
        """)
        logger.info("Converted log_entries to hypertable")
        
        # Create time_bucket view for easier time-series queries
        cur.execute("""
            CREATE OR REPLACE VIEW time_bucketed_stats AS
            SELECT 
                time_bucket('5 minutes', timestamp) AS bucket,
                SUM(normal_count) AS normal_count,
                SUM(anomaly_count) AS anomaly_count,
                SUM(unidentified_count) AS unidentified_count
            FROM classifications
            GROUP BY bucket
            ORDER BY bucket DESC;
        """)
        logger.info("Created time_bucketed_stats view")
        
        # Create a view for HDFS block analysis
        cur.execute("""
            CREATE OR REPLACE VIEW hdfs_block_stats AS
            SELECT 
                block_id,
                COUNT(*) as log_count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                array_agg(DISTINCT hdfs_component) as components,
                array_agg(DISTINCT log_level) as log_levels
            FROM log_entries
            WHERE block_id IS NOT NULL
            GROUP BY block_id
            ORDER BY log_count DESC;
        """)
        logger.info("Created hdfs_block_stats view")
        
        # Create a function to extract block IDs from messages
        cur.execute("""
            CREATE OR REPLACE FUNCTION extract_block_id(message TEXT)
            RETURNS TEXT AS $$
            DECLARE
                block_match TEXT;
            BEGIN
                -- Extract block IDs in the format blk_XXXXXXXXXX or blk_-XXXXXXXXXX
                SELECT substring(message FROM 'blk_-?[0-9]{10,19}') INTO block_match;
                RETURN block_match;
            END;
            $$ LANGUAGE plpgsql IMMUTABLE;
        """)
        logger.info("Created extract_block_id function")
        
        conn.close()
        logger.info("TimescaleDB setup complete")
    except Exception as e:
        logger.error(f"Error setting up TimescaleDB: {str(e)}")
        raise

if __name__ == "__main__":
    init_db()