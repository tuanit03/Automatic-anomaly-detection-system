import asyncio
import logging
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import os
import config
from database import Base, engine, get_db, AsyncSessionLocal
from routes import logs, statistics, anomalies, test_reports, slack
from services.kafka_consumer import KafkaConsumerService
from services.mock_data import MockDataGenerator
from services.db_service import DBService
from services.slack_notification_task import slack_notification_task

from fastapi.staticfiles import StaticFiles
from pathlib import Path



# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    redirect_slashes=False,
    title="Anomaly Detection Dashboard API",
    description="API for the anomaly detection dashboard",
    version="1.0.0"
)

# Add CORS middleware with enhanced configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=config.CORS_ALLOW_METHODS,
    allow_headers=config.CORS_ALLOW_HEADERS,
    expose_headers=["Content-Type", "Content-Length", "Cache-Control", "Last-Event-ID"],
    max_age=1800,  # 30 minutes cache for preflight requests
)

# Include routers
# app.include_router(logs.router, prefix="/api/logs")
# app.include_router(statistics.router, prefix="/api/statistics")
# app.include_router(anomalies.router, prefix="/api/anomalies")
app.include_router(logs.router, prefix=config.API_PREFIX)
app.include_router(statistics.router, prefix=config.API_PREFIX)
app.include_router(anomalies.router, prefix=config.API_PREFIX)
app.include_router(test_reports.router, prefix=config.API_PREFIX)
app.include_router(slack.router, prefix=config.API_PREFIX)

# Mount the reports directory to serve HTML files
ROOT_DIR = Path(__file__).parent.parent
REPORTS_DIR = ROOT_DIR / "reports"  # Path to reports directory
# Check if we're running in Docker container
if os.path.exists('/app/reports'):
    REPORTS_DIR = Path("/app/reports")  # Use absolute path for Docker container
app.mount("/reports", StaticFiles(directory=REPORTS_DIR, html=True), name="reports")

@app.get("/")
async def root():
    return {"message": "API Monitor Backend is running"}


# Create services
kafka_service = KafkaConsumerService()
mock_generator = MockDataGenerator()

@app.on_event("startup")
async def startup_event():
    # Create database tables if they don't exist
    async def init_db():
        logger.info("Creating database tables...")
        # Create tables synchronously (easier than async for schema creation)
        from sqlalchemy import create_engine
        sync_engine = create_engine(config.DB_URL)
        Base.metadata.create_all(sync_engine)
        logger.info("Database tables created")
    
    # Initialize database
    await init_db()

    # Register callbacks for Kafka messages
    async def process_log(log_entry):
        try:
            # Create a new session for each operation
            async_session = AsyncSessionLocal()
            try:
                # Save to database
                log = await DBService.save_log_entry(async_session, log_entry)
                # Broadcast to connected clients
                await logs.broadcast_log(log)
            finally:
                await async_session.close()
        except Exception as e:
            logger.error(f"Error processing log entry: {str(e)}")

    async def process_classification(classification):
        try:
            # Create a new session for each operation
            async_session = AsyncSessionLocal()
            try:
                # Save to database
                stats = await DBService.save_classification(async_session, classification)
                # Broadcast to connected clients
                await statistics.broadcast_statistics(stats)
            finally:
                await async_session.close()
        except Exception as e:
            logger.error(f"Error processing classification: {str(e)}")
            
    # Process anomaly parameters
    async def process_anomaly_param(anomaly_param):
        try:
            # Create a new session for each operation
            async_session = AsyncSessionLocal()
            try:
                # Save to database
                param = await DBService.save_anomaly_param(async_session, anomaly_param)
                # Broadcast to connected clients
                await anomalies.broadcast_anomaly(param)
            finally:
                await async_session.close()
        except Exception as e:
            logger.error(f"Error processing anomaly parameter: {str(e)}")

    # Register callbacks
    kafka_service.register_log_consumer(process_log)
    kafka_service.register_classification_consumer(process_classification)
    mock_generator.register_log_consumer(process_log)
    mock_generator.register_classification_consumer(process_classification)
    mock_generator.register_anomaly_param_consumer(process_anomaly_param)

    # Start Kafka consumer or mock data generator
    if config.MOCK_DATA_ENABLED:
        logger.info("Starting mock data generator")
        await mock_generator.start()
    else:
        logger.info("Starting Kafka consumer")
        await kafka_service.start()
    
    # Start Slack notification task
    logger.info("Starting Slack notification task")
    await slack_notification_task.start()

@app.on_event("shutdown")
async def shutdown_event():
    # Stop services
    if config.MOCK_DATA_ENABLED:
        logger.info("Stopping mock data generator")
        await mock_generator.stop()
    else:
        logger.info("Stopping Kafka consumer")
        await kafka_service.stop()
    
    # Stop Slack notification task
    logger.info("Stopping Slack notification task")
    await slack_notification_task.stop()

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)