import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

import config
from database import get_db
from models import ClassificationResponse, ClassificationCreate, TimeSeriesData
from services.db_service import DBService

router = APIRouter(prefix=f"{config.API_PREFIX}/statistics", tags=["statistics"])
router = APIRouter(prefix="/statistics", tags=["statistics"])
# router = APIRouter(tags=["statistics"])

# Configure logging
logger = logging.getLogger(__name__)

# In-memory store of connected SSE clients for real-time updates
stats_clients = []

@router.get("/classifications", response_model=List[ClassificationResponse])
async def get_classifications(
    skip: int = 0,
    limit: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get classification data with optional filtering
    """
    classifications = await DBService.get_classifications(
        db, 
        skip=skip, 
        limit=limit,
        start_time=start_time,
        end_time=end_time
    )
    return classifications

@router.get("/time-series", response_model=List[TimeSeriesData])
async def get_time_series_data(
    interval_minutes: int = Query(5, ge=1, le=60),
    hours: int = Query(24, ge=1, le=168),  # Max 7 days (168 hours)
    db: AsyncSession = Depends(get_db)
):
    """
    Get time series data aggregated by intervals
    Default: data for the past 24 hours in 5-minute intervals
    """
    time_series = await DBService.get_time_series_data(
        db,
        interval_minutes=interval_minutes,
        hours=hours
    )
    return time_series

@router.get("/summary")
async def get_summary(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary statistics for the specified time period
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # Get classifications for the time period
    classifications = await DBService.get_classifications(
        db,
        start_time=start_time,
        end_time=end_time,
        limit=10000  # High limit to get all data
    )
    
    # Calculate summary statistics
    total_events = 0
    normal_count = 0
    anomaly_count = 0
    unidentified_count = 0
    
    for cls in classifications:
        normal_count += cls.normal_count
        anomaly_count += cls.anomaly_count
        unidentified_count += cls.unidentified_count
        
    total_events = normal_count + anomaly_count + unidentified_count
    
    # Calculate percentages
    normal_percent = (normal_count / total_events * 100) if total_events > 0 else 0
    anomaly_percent = (anomaly_count / total_events * 100) if total_events > 0 else 0
    unidentified_percent = (unidentified_count / total_events * 100) if total_events > 0 else 0
    
    return {
        "total_events": total_events,
        "normal_count": normal_count,
        "anomaly_count": anomaly_count,
        "unidentified_count": unidentified_count,
        "normal_percent": round(normal_percent, 2),
        "anomaly_percent": round(anomaly_percent, 2),
        "unidentified_percent": round(unidentified_percent, 2),
        "time_period_hours": hours
    }

@router.get("/stream")
async def stream_statistics(request: Request):
    """
    Stream statistics in real-time using SSE
    """
    async def event_generator():
        # Create a new queue for this client
        queue = asyncio.Queue()
        client_id = id(queue)  # Generate unique ID for this client
        stats_clients.append(queue)
        logger.info(f"Client connected to statistics stream: {client_id}")
        
        # Initial keepalive to establish connection
        yield {
            "event": "ping",
            "id": "0",
            "data": json.dumps({"status": "connected"})
        }
        
        try:
            while True:
                # Check if client is still connected
                if await request.is_disconnected():
                    logger.info(f"Client {client_id} disconnected")
                    break
                
                # Wait for new statistics with timeout
                try:
                    stat = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Convert to dict for sending over SSE
                    stat_dict = {
                        "id": stat.id,
                        "timestamp": stat.timestamp.isoformat(),
                        "normal_count": stat.normal_count,
                        "anomaly_count": stat.anomaly_count,
                        "unidentified_count": stat.unidentified_count
                    }
                    
                    # Send the statistics as an event with proper JSON serialization
                    yield {
                        "event": "statistics",
                        "id": str(stat.id),
                        "data": json.dumps(stat_dict)
                    }
                except asyncio.TimeoutError:
                    # Send keepalive ping every 30 seconds to maintain connection
                    yield {
                        "event": "ping",
                        "id": "keepalive",
                        "data": json.dumps({"timestamp": datetime.now().isoformat()})
                    }
        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"Client {client_id} connection cancelled")
        except Exception as e:
            logger.error(f"Error in statistics stream for client {client_id}: {str(e)}")
        finally:
            # Remove client queue when connection ends
            if queue in stats_clients:
                stats_clients.remove(queue)
            logger.info(f"Client {client_id} removed from statistics stream")
    
    return EventSourceResponse(event_generator())

# Function to broadcast new statistics to all connected clients
async def broadcast_statistics(stat):
    disconnected_clients = []
    
    for i, queue in enumerate(stats_clients):
        try:
            await queue.put(stat)
        except Exception as e:
            logger.error(f"Error broadcasting statistics to client {i}: {str(e)}")
            disconnected_clients.append(queue)
    
    # Clean up disconnected clients
    for queue in disconnected_clients:
        if queue in stats_clients:
            stats_clients.remove(queue)