import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import AsyncSessionLocal
from services.db_service import DBService
from services.slack_service import slack_service

logger = logging.getLogger(__name__)

class SlackNotificationTask:
    def __init__(self):
        self.task = None
        self.running = False
        self.last_check_time = None  # Track when we last checked for new data
        self.sent_record_ids = set()  # Track IDs of records already sent to Slack
        self.auto_send_enabled = False  # Disable auto-send by default
        
    async def start(self):
        """Start the periodic Slack notification task"""
        if not config.SLACK_NOTIFICATION_ENABLED:
            logger.info("Slack notifications disabled")
            return
            
        if self.running:
            logger.warning("Slack notification task already running")
            return
            
        logger.info(f"Starting Slack notification task (interval: {config.SLACK_NOTIFICATION_INTERVAL_SECONDS}s)")
        
        # Test Slack connection first
        if not await slack_service.test_connection():
            logger.error("Failed to connect to Slack. Notification task will not start.")
            return
            
        self.running = True
        self.task = asyncio.create_task(self._notification_loop())
        
    async def stop(self):
        """Stop the periodic Slack notification task"""
        if self.task and self.running:
            logger.info("Stopping Slack notification task")
            self.running = False
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
            
    async def _notification_loop(self):
        """Main loop for checking new data - but only send manually or when enabled"""
        # Initialize last check time to current time
        self.last_check_time = datetime.now()
        
        while self.running:
            try:
                # Only auto-send if enabled, otherwise just check and log
                await self._check_new_data()
                await asyncio.sleep(config.SLACK_NOTIFICATION_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                logger.info("Slack notification task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Slack notification loop: {str(e)}")
                # Continue running even if there's an error
                await asyncio.sleep(config.SLACK_NOTIFICATION_INTERVAL_SECONDS)
                
    async def _check_new_data(self):
        """Check for new data and update tracking, but don't auto-send"""
        try:
            # Get database session
            async with AsyncSessionLocal() as db:
                current_time = datetime.now()
                
                # Check for new anomaly data since last check
                new_anomaly_params = await DBService.get_anomaly_params(
                    db,
                    classification_type="anomaly",
                    start_time=self.last_check_time,
                    limit=50  # Get more to check for new ones
                )
                
                # Check for new unidentified data since last check
                new_unidentified_params = await DBService.get_anomaly_params(
                    db,
                    classification_type="unidentified", 
                    start_time=self.last_check_time,
                    limit=50  # Get more to check for new ones
                )
                
                # Count truly new records (not yet sent)
                truly_new_anomalies = [p for p in new_anomaly_params if p.id not in self.sent_record_ids]
                truly_new_unidentified = [p for p in new_unidentified_params if p.id not in self.sent_record_ids]
                
                if len(truly_new_anomalies) > 0 or len(truly_new_unidentified) > 0:
                    logger.info(f"Found truly new data: {len(truly_new_anomalies)} new anomalies, {len(truly_new_unidentified)} new unidentified")
                    
                    # Only send if auto-send is enabled
                    if self.auto_send_enabled:
                        await self._send_new_records_to_slack(truly_new_anomalies, truly_new_unidentified)
                    else:
                        logger.info("Auto-send disabled. New data detected but not sent to Slack.")
                else:
                    logger.debug("No truly new anomaly or unidentified data since last check")
                
                # Update last check time
                self.last_check_time = current_time
                        
        except Exception as e:
            logger.error(f"Error checking for new anomaly data: {str(e)}")
    
    async def _send_new_records_to_slack(self, new_anomalies, new_unidentified):
        """Send only the new records to Slack and track them"""
        try:
            if len(new_anomalies) == 0 and len(new_unidentified) == 0:
                return
                
            # Send only new records to Slack
            success = await slack_service.send_param_table(new_anomalies, new_unidentified)
            if success:
                # Mark these records as sent
                for param in new_anomalies:
                    self.sent_record_ids.add(param.id)
                for param in new_unidentified:
                    self.sent_record_ids.add(param.id)
                    
                logger.info(f"Sent NEW records to Slack: {len(new_anomalies)} anomalies, {len(new_unidentified)} unidentified")
            else:
                logger.error("Failed to send new records to Slack")
                
        except Exception as e:
            logger.error(f"Error sending new records to Slack: {str(e)}")
    
    async def send_manual_update(self):
        """Manually trigger sending new data to Slack"""
        try:
            async with AsyncSessionLocal() as db:
                # Get all recent data
                all_anomaly_params = await DBService.get_anomaly_params(
                    db,
                    classification_type="anomaly",
                    limit=50
                )
                
                all_unidentified_params = await DBService.get_anomaly_params(
                    db,
                    classification_type="unidentified",
                    limit=50
                )
                
                # Filter out already sent records
                new_anomalies = [p for p in all_anomaly_params if p.id not in self.sent_record_ids]
                new_unidentified = [p for p in all_unidentified_params if p.id not in self.sent_record_ids]
                
                if len(new_anomalies) > 0 or len(new_unidentified) > 0:
                    await self._send_new_records_to_slack(new_anomalies, new_unidentified)
                    return True, f"Sent {len(new_anomalies)} anomalies and {len(new_unidentified)} unidentified to Slack"
                else:
                    return False, "No new data to send"
                    
        except Exception as e:
            logger.error(f"Error in manual update: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def enable_auto_send(self, enabled=True):
        """Enable or disable auto-sending"""
        self.auto_send_enabled = enabled
        logger.info(f"Auto-send {'enabled' if enabled else 'disabled'}")
    
    def clear_sent_records(self):
        """Clear the tracking of sent records (for testing)"""
        self.sent_record_ids.clear()
        logger.info("Cleared sent records tracking")
    
    async def _send_param_report(self):
        """Send current anomaly and unidentified parameters to Slack using the same data as frontend"""
        try:
            # Get database session
            async with AsyncSessionLocal() as db:
                # Use the same query logic as the frontend: get latest 20 records of each type
                # This ensures Slack shows exactly what the frontend dashboard shows
                
                # Get anomaly parameters (latest 20, same as frontend)
                anomaly_params = await DBService.get_anomaly_params(
                    db,
                    classification_type="anomaly",
                    limit=20  # Same as frontend
                )
                
                # Get unidentified parameters (latest 20, same as frontend)
                unidentified_params = await DBService.get_anomaly_params(
                    db,
                    classification_type="unidentified",
                    limit=20  # Same as frontend
                )
                
                # Send to Slack - always send to keep it synchronized with frontend
                success = await slack_service.send_param_table(anomaly_params, unidentified_params)
                if success:
                    logger.info(f"Sent synchronized param report to Slack: {len(anomaly_params)} anomalies, {len(unidentified_params)} unidentified (matches frontend)")
                else:
                    logger.error("Failed to send synchronized param report to Slack")
                        
        except Exception as e:
            logger.error(f"Error sending synchronized param report to Slack: {str(e)}")

# Global instance
slack_notification_task = SlackNotificationTask()
