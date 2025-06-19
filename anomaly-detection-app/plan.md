# Dashboard Implementation Plan

This document outlines the plan to build a comprehensive dashboard with four quadrants, each serving specific functions for monitoring data from Kafka and TimescaleDB.

## Overview

The dashboard will be divided into four quadrants:
1. Real-time Kafka log observation
2. Count of normal, anomaly, and unidentified items
3. List of known param_values classified as anomaly or unidentified
4. Time-series chart of normal, anomaly, and unidentified counts over time

## Architecture

### Database Schema (TimescaleDB)

1. **log_entries** Table
   ```sql
   CREATE TABLE log_entries (
     id SERIAL PRIMARY KEY,
     timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     message TEXT NOT NULL,
     log_level TEXT NOT NULL
   );
   SELECT create_hypertable('log_entries', 'timestamp');
   ```

2. **classifications** Table (Table A)
   ```sql
   CREATE TABLE classifications (
     id SERIAL PRIMARY KEY,
     timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     normal_count INTEGER NOT NULL,
     anomaly_count INTEGER NOT NULL,
     unidentified_count INTEGER NOT NULL
   );
   SELECT create_hypertable('classifications', 'timestamp');
   ```

3. **anomaly_params** Table
   ```sql
   CREATE TABLE anomaly_params (
     id SERIAL PRIMARY KEY,
     timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     param_value TEXT NOT NULL,
     classification_type TEXT NOT NULL CHECK (classification_type IN ('anomaly', 'unidentified'))
   );
   SELECT create_hypertable('anomaly_params', 'timestamp');
   ```

### Backend Implementation (FastAPI)

#### 1. Project Structure

```
backend/
├── app.py                 # Main FastAPI application
├── config.py              # Configuration settings
├── database.py            # Database connection
├── models.py              # Pydantic models
├── routes/
│   ├── __init__.py
│   ├── logs.py            # Log-related endpoints
│   ├── statistics.py      # Statistics endpoints
│   └── anomalies.py       # Anomaly-related endpoints
└── services/
    ├── __init__.py
    ├── kafka_consumer.py  # Kafka consumer service
    ├── mock_generator.py  # Mock data generator
    └── db_service.py      # Database service
```

#### 2. Key Components

**a. Database Connection (database.py)**
- Setup SQLAlchemy connection to TimescaleDB
- Create session factory

**b. Kafka Consumer Service (kafka_consumer.py)**
- Subscribe to Kafka topics
- Process incoming messages
- Store logs in the log_entries table
- Forward messages to SSE clients

**c. Mock Generator (mock_generator.py)**
- Generate random counts for normal, anomaly, and unidentified items
- Store data in the classifications table (Table A)
- Run on a schedule (e.g., every 5 seconds)

**d. API Routes**
- `/api/logs/stream` - SSE endpoint for real-time logs
- `/api/statistics/stream` - SSE endpoint for real-time statistics
- `/api/anomalies/list` - REST endpoint for anomaly parameters list
- `/api/statistics/timeseries` - REST endpoint for time-series data

### Frontend Implementation (React)

#### 1. Project Structure

```
frontend/
├── public/
└── src/
    ├── App.js
    ├── index.js
    ├── components/
    │   ├── Dashboard.js           # Main dashboard layout
    │   ├── LogViewer.js           # Quadrant 1: Log viewer
    │   ├── StatisticsCounter.js   # Quadrant 2: Count statistics
    │   ├── AnomalyList.js         # Quadrant 3: Anomaly parameters list
    │   └── TimeSeriesChart.js     # Quadrant 4: Time-series chart
    ├── services/
    │   ├── api.js                 # API client
    │   └── eventSource.js         # SSE client
    └── utils/
        ├── formatters.js          # Data formatters
        └── colors.js              # Color constants
```

#### 2. Key Components

**a. Dashboard Layout (Dashboard.js)**
- Grid layout with four quadrants
- Responsive design

**b. LogViewer Component (LogViewer.js)**
- Connect to SSE endpoint for real-time logs
- Auto-scrolling log display
- Color-coded logs based on level

**c. StatisticsCounter Component (StatisticsCounter.js)**
- Connect to SSE endpoint for real-time statistics
- Three circles with counts
- Color-coded: green (normal), red (anomaly), yellow (unidentified)

**d. AnomalyList Component (AnomalyList.js)**
- Fetch data from REST endpoint
- Display table of param_values
- Auto-refresh every 10 seconds

**e. TimeSeriesChart Component (TimeSeriesChart.js)**
- Fetch data from REST endpoint
- Use a charting library (e.g., Chart.js, Recharts)
- Three lines for normal, anomaly, and unidentified counts
- Auto-refresh hourly

## Implementation Steps

### Phase 1: Database Setup

1. Update the `/home/dev/DoAn6/kafka/database/init-db.sql` file with the schema defined above
2. Test database connection from Docker containers

### Phase 2: Backend Development

1. Install required Python packages in requirements.txt
   ```
   fastapi>=0.68.0
   uvicorn>=0.15.0
   sqlalchemy>=1.4.23
   psycopg2-binary>=2.9.1
   pydantic>=1.8.2
   python-dateutil>=2.8.2
   kafka-python>=2.0.2
   requests>=2.26.0
   sse-starlette>=0.10.3
   asyncpg>=0.25.0
   ```

2. Create database connection module
3. Implement Kafka consumer service
4. Implement mock data generator
5. Create API endpoints for SSE and REST
6. Test endpoints with tools like curl or Postman

### Phase 3: Frontend Development

1. Install required npm packages
   ```bash
   npm install axios recharts date-fns
   ```

2. Create the main dashboard layout
3. Implement the four quadrant components:
   - LogViewer
   - StatisticsCounter
   - AnomalyList
   - TimeSeriesChart
4. Connect components to backend endpoints
5. Style the components with CSS or a UI framework

### Phase 4: Integration and Testing

1. Run the complete stack with Docker Compose
2. Test real-time updates from Kafka
3. Verify data persistence in TimescaleDB
4. Ensure all four quadrants update correctly
5. Test responsiveness and performance

## Detailed Component Implementations

### Backend Components

#### SSE Implementation for Logs and Statistics

```python
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
import asyncio
from datetime import datetime

router = APIRouter()

@router.get("/stream")
async def stream_logs():
    async def event_generator():
        while True:
            # Get latest logs from database or Kafka consumer
            logs = await get_latest_logs()
            if logs:
                yield {"event": "log", "data": logs}
            await asyncio.sleep(1)
    
    return EventSourceResponse(event_generator())

@router.get("/statistics/stream")
async def stream_statistics():
    async def event_generator():
        while True:
            # Generate mock statistics data and save to DB
            stats = await generate_and_save_stats()
            if stats:
                yield {"event": "stats", "data": stats}
            await asyncio.sleep(5)
    
    return EventSourceResponse(event_generator())
```

#### Mock Data Generator

```python
import random
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

async def generate_mock_data(db: AsyncSession):
    while True:
        # Generate random counts
        normal = random.randint(10, 100)
        anomaly = random.randint(0, 20)
        unidentified = random.randint(0, 10)
        
        # Save to database
        await save_classifications(db, normal, anomaly, unidentified)
        
        # Generate random anomaly parameters
        for _ in range(random.randint(0, 3)):
            param_value = f"param_{random.randint(1000, 9999)}"
            classification = random.choice(["anomaly", "unidentified"])
            await save_anomaly_param(db, param_value, classification)
        
        # Wait before next generation
        await asyncio.sleep(5)
```

### Frontend Components

#### LogViewer Component

```jsx
import React, { useEffect, useState, useRef } from 'react';
import { connectToSSE } from '../services/eventSource';

const LogViewer = () => {
  const [logs, setLogs] = useState([]);
  const logContainerRef = useRef(null);
  
  useEffect(() => {
    const eventSource = connectToSSE('/api/logs/stream');
    
    eventSource.addEventListener('log', (event) => {
      const newLog = JSON.parse(event.data);
      setLogs((prevLogs) => [...prevLogs.slice(-99), newLog]);
    });
    
    return () => {
      eventSource.close();
    };
  }, []);
  
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);
  
  return (
    <div className="log-viewer">
      <h2>Real-time Logs</h2>
      <div className="log-container" ref={logContainerRef}>
        {logs.map((log, index) => (
          <div key={index} className={`log-entry log-${log.log_level}`}>
            <span className="timestamp">{new Date(log.timestamp).toLocaleTimeString()}</span>
            <span className="message">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LogViewer;
```

#### StatisticsCounter Component

```jsx
import React, { useEffect, useState } from 'react';
import { connectToSSE } from '../services/eventSource';

const StatisticsCounter = () => {
  const [stats, setStats] = useState({
    normal_count: 0,
    anomaly_count: 0,
    unidentified_count: 0
  });
  
  useEffect(() => {
    const eventSource = connectToSSE('/api/statistics/stream');
    
    eventSource.addEventListener('stats', (event) => {
      const newStats = JSON.parse(event.data);
      setStats(newStats);
    });
    
    return () => {
      eventSource.close();
    };
  }, []);
  
  return (
    <div className="statistics-counter">
      <h2>Classification Counts</h2>
      <div className="circles-container">
        <div className="circle normal">
          <div className="count">{stats.normal_count}</div>
          <div className="label">Normal</div>
        </div>
        <div className="circle anomaly">
          <div className="count">{stats.anomaly_count}</div>
          <div className="label">Anomaly</div>
        </div>
        <div className="circle unidentified">
          <div className="count">{stats.unidentified_count}</div>
          <div className="label">Unidentified</div>
        </div>
      </div>
    </div>
  );
};

export default StatisticsCounter;
```

## Conclusion

This plan provides a comprehensive blueprint for building the dashboard with all four quadrants. By following the implementation steps and leveraging the technologies defined in the Docker Compose setup, you'll be able to create a powerful monitoring dashboard that visualizes real-time data from Kafka and TimescaleDB.

The implementation uses modern web technologies: FastAPI for the backend, React for the frontend, and TimescaleDB for time-series data storage. Server-Sent Events (SSE) are used for real-time updates, providing an efficient way to stream data from the server to the client.

The mock data generator will simulate real-world data until the actual Kafka pipeline is fully implemented. This approach allows for parallel development and testing of the dashboard components.