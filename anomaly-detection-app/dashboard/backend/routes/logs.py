import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

import config
from database import get_db
from models import LogEntryResponse, LogEntryCreate
from services.db_service import DBService

# router = APIRouter(prefix=f"{config.API_PREFIX}/logs", tags=["logs"])
router = APIRouter(prefix="/logs", tags=["logs"])
# router = APIRouter(tags=["logs"])

# Configure logging
logger = logging.getLogger(__name__)

# In-memory store of connected SSE clients for real-time updates
log_clients = []

@router.get("/", response_model=List[LogEntryResponse])
async def get_logs(
    skip: int = 0,
    limit: int = 100,
    log_level: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get log entries with optional filtering
    """
    logs = await DBService.get_log_entries(
        db, 
        skip=skip, 
        limit=limit,
        log_level=log_level,
        start_time=start_time,
        end_time=end_time
    )
    return logs

@router.get("/stream")
async def stream_logs(request: Request):
    """
    Stream logs in real-time using SSE
    """
    async def event_generator():
        # Create a new queue for this client
        queue = asyncio.Queue()
        client_id = id(queue)  # Generate unique ID for this client
        log_clients.append(queue)
        logger.info(f"Client connected to logs stream: {client_id}")
        
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
                    
                # Wait for new logs with timeout
                try:
                    log = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Convert to dict for sending over SSE
                    log_dict = {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "message": log.message,
                        "log_level": log.log_level
                    }
                    
                    # Send the log as an event with proper JSON serialization
                    yield {
                        "event": "log",
                        "id": str(log.id),
                        "data": json.dumps(log_dict)
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
            logger.error(f"Error in log stream for client {client_id}: {str(e)}")
        finally:
            # Remove client queue when connection ends
            if queue in log_clients:
                log_clients.remove(queue)
            logger.info(f"Client {client_id} removed from logs stream")
    
    return EventSourceResponse(event_generator())

# Function to broadcast new logs to all connected clients
async def broadcast_log(log):
    disconnected_clients = []
    
    for i, queue in enumerate(log_clients):
        try:
            await queue.put(log)
        except Exception as e:
            logger.error(f"Error broadcasting log to client {i}: {str(e)}")
            disconnected_clients.append(queue)
    
    # Clean up disconnected clients
    for queue in disconnected_clients:
        if queue in log_clients:
            log_clients.remove(queue)