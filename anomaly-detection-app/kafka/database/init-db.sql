-- Initialize the TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create the log_entries table for storing HDFS logs
CREATE TABLE log_entries (
  id SERIAL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  message TEXT NOT NULL,
  log_level TEXT NOT NULL,
  hdfs_date CHAR(6),           -- YYMMDD format
  hdfs_time CHAR(6),           -- HHMMSS format
  thread_id INTEGER,           -- Thread ID from HDFS log
  hdfs_component TEXT,         -- HDFS component name
  block_id TEXT,               -- HDFS block ID (if present)
  PRIMARY KEY (id, timestamp)  -- Modified: timestamp is now part of the primary key
);

-- Convert log_entries to a hypertable
SELECT create_hypertable('log_entries', 'timestamp');

-- Create the classifications table for counts of normal, anomaly, and unidentified items
CREATE TABLE classifications (
  id SERIAL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  normal_count INTEGER NOT NULL,
  anomaly_count INTEGER NOT NULL,
  unidentified_count INTEGER NOT NULL,
  PRIMARY KEY (id, timestamp)  -- Modified: timestamp is now part of the primary key
);

-- Convert classifications to a hypertable
SELECT create_hypertable('classifications', 'timestamp');

-- Create the anomaly_params table for tracking anomaly and unidentified parameters
CREATE TABLE anomaly_params (
  id SERIAL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  param_value TEXT NOT NULL,
  classification_type TEXT NOT NULL CHECK (classification_type IN ('anomaly', 'unidentified')),
  PRIMARY KEY (id, timestamp)  -- Modified: timestamp is now part of the primary key
);

-- Convert anomaly_params to a hypertable
SELECT create_hypertable('anomaly_params', 'timestamp');

-- Create indexes for better query performance
CREATE INDEX ON log_entries (log_level, timestamp DESC);
CREATE INDEX ON log_entries (hdfs_component, timestamp DESC);
CREATE INDEX ON log_entries (block_id, timestamp DESC);
CREATE INDEX ON classifications (timestamp DESC);
CREATE INDEX ON anomaly_params (classification_type, timestamp DESC);

-- Add comment to explain the purpose of these tables
COMMENT ON TABLE log_entries IS 'Stores log messages from Kafka for real-time observation';
COMMENT ON TABLE classifications IS 'Tracks counts of normal, anomaly, and unidentified items over time';
COMMENT ON TABLE anomaly_params IS 'Lists parameter values classified as anomaly or unidentified';