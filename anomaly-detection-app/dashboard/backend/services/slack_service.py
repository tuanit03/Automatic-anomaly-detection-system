import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

import config
from models import AnomalyParamResponse

logger = logging.getLogger(__name__)

class SlackService:
    def __init__(self):
        self.client = None
        self.enabled = config.SLACK_NOTIFICATION_ENABLED
        
        if self.enabled and config.SLACK_BOT_TOKEN:
            self.client = AsyncWebClient(token=config.SLACK_BOT_TOKEN)
            logger.info("Slack service initialized")
        else:
            logger.warning("Slack service disabled or token not provided")
    
    async def send_param_table(self, anomaly_params: List[AnomalyParamResponse], unidentified_params: List[AnomalyParamResponse]):
        """
        Send a formatted table of anomaly and unidentified parameters to Slack
        """
        if not self.enabled or not self.client or not config.SLACK_CHANNEL_ID:
            logger.warning("Slack service not configured properly")
            return False
            
        try:
            # Create formatted message
            message = self._format_param_table(anomaly_params, unidentified_params)
            
            # Send message to Slack
            response = await self.client.chat_postMessage(
                channel=config.SLACK_CHANNEL_ID,
                text=message,
                parse="none"
            )
            
            if response["ok"]:
                logger.info(f"Successfully sent param table to Slack channel {config.SLACK_CHANNEL_ID}")
                return True
            else:
                logger.error(f"Failed to send message to Slack: {response.get('error', 'Unknown error')}")
                return False
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending message to Slack: {str(e)}")
            return False
    
    def _format_param_table(self, anomaly_params: List[AnomalyParamResponse], unidentified_params: List[AnomalyParamResponse]) -> str:
        """
        Format the parameter data into a readable table for Slack
        Simplified format as requested
        """
        # Use UTC+7 timezone like frontend (Vietnamese timezone)
        from datetime import timezone, timedelta
        vn_tz = timezone(timedelta(hours=7))
        current_time = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        message_parts = [
            f"Anomaly Detection Report - {current_time}",
            ""
        ]
        
        # Anomaly parameters section
        if anomaly_params:
            message_parts.extend([
                ":red_circle: ANOMALY PARAMETERS"
            ])
            
            for param in anomaly_params[:20]:  # Show up to 20 entries like frontend
                # Format timestamp like frontend: convert to Vietnamese timezone and use toLocaleString format
                param_timestamp = param.timestamp.replace(tzinfo=timezone.utc).astimezone(vn_tz)
                timestamp_str = param_timestamp.strftime("%m/%d/%Y, %I:%M:%S %p")
                
                # Show full param_value without truncation
                param_value = str(param.param_value)
                
                message_parts.append(f"{timestamp_str}")
                message_parts.append(f"{param_value}")
                message_parts.append("")  # Empty line between entries
            
            if len(anomaly_params) > 20:
                message_parts.append(f"... and {len(anomaly_params) - 20} more anomaly parameters")
                
            message_parts.append("")
        
        # Unidentified parameters section
        if unidentified_params:
            message_parts.extend([
                ":large_yellow_circle: UNIDENTIFIED PARAMETERS"
            ])
            
            for param in unidentified_params[:20]:  # Show up to 20 entries like frontend
                # Format timestamp like frontend: convert to Vietnamese timezone and use toLocaleString format
                param_timestamp = param.timestamp.replace(tzinfo=timezone.utc).astimezone(vn_tz)
                timestamp_str = param_timestamp.strftime("%m/%d/%Y, %I:%M:%S %p")
                
                # Show full param_value without truncation
                param_value = str(param.param_value)
                
                message_parts.append(f"{timestamp_str}")
                message_parts.append(f"{param_value}")
                message_parts.append("")  # Empty line between entries
            
            if len(unidentified_params) > 20:
                message_parts.append(f"... and {len(unidentified_params) - 20} more unidentified parameters")
        
        return "\n".join(message_parts)
    
    async def test_connection(self) -> bool:
        """
        Test the Slack connection
        """
        if not self.enabled or not self.client:
            return False
            
        try:
            response = await self.client.auth_test()
            if response["ok"]:
                logger.info(f"Slack connection test successful. Bot: {response.get('user', 'Unknown')}")
                return True
            else:
                logger.error(f"Slack connection test failed: {response.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Error testing Slack connection: {str(e)}")
            return False

# Global instance
slack_service = SlackService()
