import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func, desc, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from models import (
    LogEntry, LogEntryCreate, LogEntryResponse,
    Classification, ClassificationCreate, ClassificationResponse,
    AnomalyParam, AnomalyParamCreate, AnomalyParamResponse,
    TimeSeriesData
)

logger = logging.getLogger(__name__)

class DBService:
    @staticmethod
    async def save_log_entry(db: AsyncSession, log_entry: LogEntryCreate) -> LogEntry:
        """Save a log entry to the database"""
        db_log_entry = LogEntry(
            message=log_entry.message,
            log_level=log_entry.log_level
        )
        db.add(db_log_entry)
        await db.commit()
        await db.refresh(db_log_entry)
        return db_log_entry
        
    @staticmethod
    async def save_classification(db: AsyncSession, classification: ClassificationCreate) -> Classification:
        """Save a classification to the database"""
        db_classification = Classification(
            normal_count=classification.normal_count,
            anomaly_count=classification.anomaly_count,
            unidentified_count=classification.unidentified_count
        )
        db.add(db_classification)
        await db.commit()
        await db.refresh(db_classification)
        return db_classification
        
    @staticmethod
    async def save_anomaly_param(db: AsyncSession, anomaly_param: AnomalyParamCreate) -> AnomalyParam:
        """Save an anomaly parameter to the database"""
        db_anomaly_param = AnomalyParam(
            param_value=anomaly_param.param_value,
            classification_type=anomaly_param.classification_type
        )
        db.add(db_anomaly_param)
        await db.commit()
        await db.refresh(db_anomaly_param)
        return db_anomaly_param
        
    @staticmethod
    async def get_log_entries(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        log_level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filter_query: Optional[str] = None
    ) -> List[LogEntry]:
        """Get log entries with optional filtering"""
        query = select(LogEntry).order_by(desc(LogEntry.timestamp))
        
        # Apply filters if provided
        if log_level:
            query = query.where(LogEntry.log_level == log_level)
            
        if start_time:
            query = query.where(LogEntry.timestamp >= start_time)
            
        if end_time:
            query = query.where(LogEntry.timestamp <= end_time)
            
        # Apply custom filter query if provided
        if filter_query:
            query = query.where(text(filter_query))
            
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
        
    @staticmethod
    async def get_classifications(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Classification]:
        """Get classifications with optional filtering"""
        query = select(Classification).order_by(desc(Classification.timestamp))
        
        # Apply filters if provided
        if start_time:
            query = query.where(Classification.timestamp >= start_time)
            
        if end_time:
            query = query.where(Classification.timestamp <= end_time)
            
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
        
    @staticmethod
    async def get_anomaly_params(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        classification_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AnomalyParam]:
        """Get anomaly parameters with optional filtering"""
        query = select(AnomalyParam).order_by(desc(AnomalyParam.timestamp))
        
        # Apply filters if provided
        if classification_type:
            query = query.where(AnomalyParam.classification_type == classification_type)
            
        if start_time:
            query = query.where(AnomalyParam.timestamp >= start_time)
            
        if end_time:
            query = query.where(AnomalyParam.timestamp <= end_time)
            
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
        
    @staticmethod
    async def get_time_series_data(
        db: AsyncSession,
        interval_minutes: int = 5,
        hours: int = 24
    ) -> List[TimeSeriesData]:
        """
        Get time series data aggregated by intervals
        Default: data for the past 24 hours in 5-minute intervals
        """
        # Calculate start time
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Use TimescaleDB time_bucket function if available
        try:
            # TimescaleDB specific query
            query = text(f"""
                SELECT 
                    time_bucket('{interval_minutes} minutes'::interval, timestamp) as bucket_time,
                    COALESCE(SUM(normal_count), 0) as normal_count,
                    COALESCE(SUM(anomaly_count), 0) as anomaly_count,
                    COALESCE(SUM(unidentified_count), 0) as unidentified_count
                FROM 
                    classifications
                WHERE 
                    timestamp BETWEEN :start_time AND :end_time
                GROUP BY 
                    bucket_time
                ORDER BY 
                    bucket_time ASC
            """)
            
            result = await db.execute(
                query, 
                {"start_time": start_time, "end_time": end_time}
            )
            rows = result.fetchall()
            
            # Convert to TimeSeriesData objects
            return [
                TimeSeriesData(
                    timestamp=row[0],
                    normal_count=row[1],
                    anomaly_count=row[2],
                    unidentified_count=row[3]
                ) for row in rows
            ]
            
        except Exception as e:
            logger.warning(f"TimescaleDB time_bucket failed, falling back to standard SQL: {str(e)}")
            
            # Fall back to standard SQL for non-TimescaleDB databases
            # This is less efficient but works with any PostgreSQL database
            # Note: This SQL is specific to PostgreSQL
            query = text(f"""
                SELECT 
                    date_trunc('hour', timestamp) + 
                    INTERVAL '1 minute' * (EXTRACT(MINUTE FROM timestamp)::INTEGER / :interval_minutes * :interval_minutes) 
                    as bucket_time,
                    COALESCE(SUM(normal_count), 0) as normal_count,
                    COALESCE(SUM(anomaly_count), 0) as anomaly_count,
                    COALESCE(SUM(unidentified_count), 0) as unidentified_count
                FROM 
                    classifications
                WHERE 
                    timestamp BETWEEN :start_time AND :end_time
                GROUP BY 
                    bucket_time
                ORDER BY 
                    bucket_time ASC
            """)
            
            result = await db.execute(
                query, 
                {"interval_minutes": interval_minutes, "start_time": start_time, "end_time": end_time}
            )
            rows = result.fetchall()
            
            # Convert to TimeSeriesData objects
            return [
                TimeSeriesData(
                    timestamp=row[0],
                    normal_count=row[1],
                    anomaly_count=row[2],
                    unidentified_count=row[3]
                ) for row in rows
            ]