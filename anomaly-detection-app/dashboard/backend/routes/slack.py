import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

import config
from database import get_db
from services.slack_service import slack_service
from services.slack_notification_task import slack_notification_task
from services.db_service import DBService

router = APIRouter(prefix="/slack", tags=["slack"])

logger = logging.getLogger(__name__)

@router.get("/status")
async def get_slack_status():
    """
    Get Slack integration status
    """
    return {
        "enabled": config.SLACK_NOTIFICATION_ENABLED,
        "bot_token_configured": bool(config.SLACK_BOT_TOKEN),
        "channel_configured": bool(config.SLACK_CHANNEL_ID),
        "interval_seconds": config.SLACK_NOTIFICATION_INTERVAL_SECONDS,
        "task_running": slack_notification_task.running,
        "auto_send_enabled": slack_notification_task.auto_send_enabled,
        "sent_records_count": len(slack_notification_task.sent_record_ids)
    }

@router.post("/test-connection")
async def test_slack_connection():
    """
    Test the Slack connection
    """
    if not config.SLACK_NOTIFICATION_ENABLED:
        raise HTTPException(status_code=400, detail="Slack notifications are disabled")
    
    if not config.SLACK_BOT_TOKEN or not config.SLACK_CHANNEL_ID:
        raise HTTPException(status_code=400, detail="Slack bot token or channel ID not configured")
    
    success = await slack_service.test_connection()
    
    if success:
        return {"status": "success", "message": "Slack connection test successful"}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to Slack")

@router.post("/send-test-message")
async def send_test_message(db: AsyncSession = Depends(get_db)):
    """
    Send a test message with current param data to Slack using the same parameters as frontend
    """
    if not config.SLACK_NOTIFICATION_ENABLED:
        raise HTTPException(status_code=400, detail="Slack notifications are disabled")
    
    try:
        # Get anomaly parameters with same params as frontend (limit 20, latest data)
        anomaly_params = await DBService.get_anomaly_params(
            db,
            classification_type="anomaly",
            limit=20
        )
        
        # Get unidentified parameters with same params as frontend (limit 20, latest data)
        unidentified_params = await DBService.get_anomaly_params(
            db,
            classification_type="unidentified",
            limit=20
        )
        
        # Send test message
        success = await slack_service.send_param_table(anomaly_params, unidentified_params)
        
        if success:
            return {
                "status": "success", 
                "message": f"Test message sent successfully with {len(anomaly_params)} anomalies and {len(unidentified_params)} unidentified parameters (same data as frontend)"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send test message to Slack")
            
    except Exception as e:
        logger.error(f"Error sending test message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending test message: {str(e)}")

@router.post("/start-notifications")
async def start_notifications():
    """
    Start Slack notification task
    """
    if not config.SLACK_NOTIFICATION_ENABLED:
        raise HTTPException(status_code=400, detail="Slack notifications are disabled")
    
    if slack_notification_task.running:
        return {"status": "info", "message": "Slack notifications are already running"}
    
    try:
        await slack_notification_task.start()
        return {"status": "success", "message": "Slack notifications started"}
    except Exception as e:
        logger.error(f"Error starting Slack notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting notifications: {str(e)}")

@router.post("/stop-notifications")
async def stop_notifications():
    """
    Stop Slack notification task
    """
    if not slack_notification_task.running:
        return {"status": "info", "message": "Slack notifications are not running"}
    
    try:
        await slack_notification_task.stop()
        return {"status": "success", "message": "Slack notifications stopped"}
    except Exception as e:
        logger.error(f"Error stopping Slack notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping notifications: {str(e)}")

@router.post("/send-new-data")
async def send_new_data_to_slack():
    """
    Manually send only new (unsent) data to Slack
    """
    if not config.SLACK_NOTIFICATION_ENABLED:
        raise HTTPException(status_code=400, detail="Slack notifications are disabled")
    
    try:
        success, message = await slack_notification_task.send_manual_update()
        
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "no_data", "message": message}
            
    except Exception as e:
        logger.error(f"Error sending new data to Slack: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending new data: {str(e)}")

@router.post("/toggle-auto-send")
async def toggle_auto_send(enabled: bool = Query(True, description="Enable or disable auto-sending")):
    """
    Enable or disable automatic sending of new data to Slack
    """
    try:
        slack_notification_task.enable_auto_send(enabled)
        return {
            "status": "success", 
            "message": f"Auto-send {'enabled' if enabled else 'disabled'}",
            "auto_send_enabled": enabled
        }
    except Exception as e:
        logger.error(f"Error toggling auto-send: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error toggling auto-send: {str(e)}")

@router.post("/clear-sent-records")
async def clear_sent_records():
    """
    Clear the tracking of sent records (for testing purposes)
    """
    try:
        slack_notification_task.clear_sent_records()
        return {"status": "success", "message": "Cleared sent records tracking"}
    except Exception as e:
        logger.error(f"Error clearing sent records: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing sent records: {str(e)}")
