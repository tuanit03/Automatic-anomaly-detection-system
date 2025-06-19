from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from database import Base

# SQLAlchemy Models
class LogEntry(Base):
    __tablename__ = "log_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    message = Column(String(1024), nullable=False)
    log_level = Column(String(20), default="INFO", index=True)

class Classification(Base):
    __tablename__ = "classifications"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    normal_count = Column(Integer, default=0)
    anomaly_count = Column(Integer, default=0)
    unidentified_count = Column(Integer, default=0)
    
    # Hypertable configuration for TimescaleDB
    __table_args__ = {
        'info': {
            'timescaledb.hypertable': True,
            'timescaledb.time_column': 'timestamp',
        }
    }

class AnomalyParam(Base):
    __tablename__ = "anomaly_params"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    param_value = Column(String(1024), nullable=False)
    classification_type = Column(String(20), default="anomaly", index=True)  # "anomaly" or "unidentified"

# Pydantic Models for API

# Log Entries
class LogEntryBase(BaseModel):
    message: str
    log_level: str = "INFO"

class LogEntryCreate(LogEntryBase):
    pass

class LogEntryResponse(LogEntryBase):
    id: int
    timestamp: datetime
    
    class Config:
        orm_mode = True

# Classifications
class ClassificationBase(BaseModel):
    normal_count: int = 0
    anomaly_count: int = 0
    unidentified_count: int = 0

class ClassificationCreate(ClassificationBase):
    pass

class ClassificationResponse(ClassificationBase):
    id: int
    timestamp: datetime
    
    class Config:
        orm_mode = True

# Anomaly Parameters
class AnomalyParamBase(BaseModel):
    param_value: str
    classification_type: str = "anomaly"  # "anomaly" or "unidentified"

class AnomalyParamCreate(AnomalyParamBase):
    pass

class AnomalyParamResponse(AnomalyParamBase):
    id: int
    timestamp: datetime
    
    class Config:
        orm_mode = True

# Time Series Data
class TimeSeriesData(BaseModel):
    timestamp: datetime
    normal_count: int = 0
    anomaly_count: int = 0
    unidentified_count: int = 0