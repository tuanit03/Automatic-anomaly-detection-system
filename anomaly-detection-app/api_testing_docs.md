# Dashboard API Documentation

This document describes the available API endpoints for the Dashboard application, detailing their methods and input parameters.

## API Base URL

All endpoints are prefixed with: `/api`

## Logs API

### GET /api/logs/
**Description**: Retrieves log entries with optional filtering.

**Parameters**:
- `skip` (integer, optional): Number of records to skip. Default: 0
- `limit` (integer, optional): Maximum number of records to return. Default: 100
- `log_level` (string, optional): Filter by log level (e.g., "INFO", "ERROR", "WARNING")
- `start_time` (datetime, optional): Filter logs after this timestamp
- `end_time` (datetime, optional): Filter logs before this timestamp

**Response**: List of log entries containing id, timestamp, message, and log_level.

### GET /api/logs/stream
**Description**: Server-Sent Events (SSE) endpoint that streams logs in real-time.

**Parameters**: None

**Response Format**: SSE stream with events containing log data:
- `event`: "log" for log entries, "ping" for keepalive
- `data`: JSON object with id, timestamp, message, and log_level

## Statistics API

### GET /api/statistics/classifications
**Description**: Retrieves classification data entries with optional filtering.

**Parameters**:
- `skip` (integer, optional): Number of records to skip. Default: 0
- `limit` (integer, optional): Maximum number of records to return. Default: 100
- `start_time` (datetime, optional): Filter entries after this timestamp
- `end_time` (datetime, optional): Filter entries before this timestamp

**Response**: List of classification entries containing id, timestamp, normal_count, anomaly_count, and unidentified_count.

### GET /api/statistics/time-series
**Description**: Gets time-series data aggregated by time intervals.

**Parameters**:
- `interval_minutes` (integer, optional): Size of time buckets in minutes. Default: 5, Range: 1-60
- `hours` (integer, optional): How many hours of historical data to retrieve. Default: 24, Range: 1-168

**Response**: List of time series points containing timestamp, normal_count, anomaly_count, and unidentified_count.

### GET /api/statistics/summary
**Description**: Retrieves summary statistics for a specified time period.

**Parameters**:
- `hours` (integer, optional): How many hours of historical data to include. Default: 24, Range: 1-168

**Response**: Single object containing:
- `total_events` (integer): Total number of events
- `normal_count` (integer): Number of normal events
- `anomaly_count` (integer): Number of anomaly events
- `unidentified_count` (integer): Number of unidentified events
- `normal_percent` (float): Percentage of normal events
- `anomaly_percent` (float): Percentage of anomaly events
- `unidentified_percent` (float): Percentage of unidentified events
- `time_period_hours` (integer): The time period used for calculations

### GET /api/statistics/stream
**Description**: Server-Sent Events (SSE) endpoint that streams statistics updates in real-time.

**Parameters**: None

**Response Format**: SSE stream with events containing statistical data:
- `event`: "statistics" for statistics updates, "ping" for keepalive
- `data`: JSON object with id, timestamp, normal_count, anomaly_count, and unidentified_count

## Anomalies API

### GET /api/anomalies/
**Description**: Retrieves anomaly parameters with optional filtering.

**Parameters**:
- `skip` (integer, optional): Number of records to skip. Default: 0
- `limit` (integer, optional): Maximum number of records to return. Default: 100
- `classification_type` (string, optional): Filter by classification type ("anomaly" or "unidentified")
- `start_time` (datetime, optional): Filter entries after this timestamp
- `end_time` (datetime, optional): Filter entries before this timestamp

**Response**: List of anomaly parameter entries containing id, timestamp, param_value, and classification_type.

### GET /api/anomalies/recent
**Description**: Gets recent anomaly parameters within a specified time period.

**Parameters**:
- `hours` (integer, optional): How many hours of historical data to retrieve. Default: 24, Range: 1-168
- `limit` (integer, optional): Maximum number of records to return. Default: 10, Range: 1-100

**Response**: List of anomaly parameter entries filtered to "anomaly" classification type.

### GET /api/anomalies/unidentified
**Description**: Gets recent unidentified parameters within a specified time period.

**Parameters**:
- `hours` (integer, optional): How many hours of historical data to retrieve. Default: 24, Range: 1-168
- `limit` (integer, optional): Maximum number of records to return. Default: 10, Range: 1-100

**Response**: List of anomaly parameter entries filtered to "unidentified" classification type.

### GET /api/anomalies/stream
**Description**: Server-Sent Events (SSE) endpoint that streams anomaly parameter updates in real-time.

**Parameters**: None

**Response Format**: SSE stream with events containing anomaly data:
- `event`: "anomaly" for anomaly updates, "ping" for keepalive
- `data`: JSON object with id, timestamp, param_value, and classification_type
