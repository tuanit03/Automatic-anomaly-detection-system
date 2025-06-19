import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Callable
from kafka import KafkaConsumer, TopicPartition
from sqlalchemy.ext.asyncio import AsyncSession

import config
from models import LogEntryCreate, ClassificationCreate, AnomalyParamCreate

logger = logging.getLogger(__name__)

class KafkaConsumerService:
    def __init__(self):
        self.log_consumers = []
        self.classification_consumers = []
        self.running = False
        self.consumer_tasks = []
        
    def create_consumer(self, topic: str, group_id: str):
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS.split(','),
                group_id=group_id,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            consumer.subscribe([topic])
            return consumer
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer: {str(e)}")
            return None
            
    def register_log_consumer(self, callback: Callable):
        """Register a callback for log messages"""
        self.log_consumers.append(callback)
        
    def register_classification_consumer(self, callback: Callable):
        """Register a callback for classification messages"""
        self.classification_consumers.append(callback)
        
    async def start(self):
        """Start consuming messages from Kafka topics"""
        if self.running:
            return
            
        self.running = True
        
        log_consumer_task = asyncio.create_task(
            self._consume_logs(config.KAFKA_TOPIC_LOGS, f"{config.KAFKA_CONSUMER_GROUP}-logs")
        )
        
        classification_consumer_task = asyncio.create_task(
            self._consume_classifications(
                config.KAFKA_TOPIC_CLASSIFICATIONS, 
                f"{config.KAFKA_CONSUMER_GROUP}-classifications"
            )
        )
        
        self.consumer_tasks = [log_consumer_task, classification_consumer_task]
        
    async def _consume_logs(self, topic: str, group_id: str):
        """Consume log messages from Kafka"""
        consumer = self.create_consumer(topic, group_id)
        if not consumer:
            logger.error(f"Failed to create consumer for topic {topic}")
            return
            
        logger.info(f"Started consuming from {topic}")
        
        while self.running:
            try:
                # Non-blocking poll with timeout
                messages = consumer.poll(timeout_ms=1000, max_records=10)
                
                for partition_data in messages.values():
                    for message in partition_data:
                        data = message.value
                        log_entry = LogEntryCreate(
                            message=data.get('message', ''),
                            log_level=data.get('level', 'INFO')
                        )
                        
                        # Notify all registered consumers
                        for callback in self.log_consumers:
                            await callback(log_entry)
                            
                # Sleep a bit to avoid high CPU usage
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error consuming from {topic}: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
                
        if consumer:
            consumer.close()
            
    async def _consume_classifications(self, topic: str, group_id: str):
        """Consume classification messages from Kafka"""
        consumer = self.create_consumer(topic, group_id)
        if not consumer:
            logger.error(f"Failed to create consumer for topic {topic}")
            return
            
        logger.info(f"Started consuming from {topic}")
        
        while self.running:
            try:
                # Non-blocking poll with timeout
                messages = consumer.poll(timeout_ms=1000, max_records=10)
                
                for partition_data in messages.values():
                    for message in partition_data:
                        data = message.value
                        
                        classification = ClassificationCreate(
                            normal_count=data.get('normal', 0),
                            anomaly_count=data.get('anomaly', 0),
                            unidentified_count=data.get('unidentified', 0)
                        )
                        
                        # Process anomaly parameters if present
                        anomaly_params = data.get('anomaly_params', [])
                        if anomaly_params:
                            for param in anomaly_params:
                                anomaly_param = AnomalyParamCreate(
                                    param_value=str(param.get('value', '')),
                                    classification_type='anomaly'
                                )
                                # TODO: Save anomaly parameters to database
                        
                        # Process unidentified parameters if present
                        unidentified_params = data.get('unidentified_params', [])
                        if unidentified_params:
                            for param in unidentified_params:
                                unidentified_param = AnomalyParamCreate(
                                    param_value=str(param.get('value', '')),
                                    classification_type='unidentified'
                                )
                                # TODO: Save unidentified parameters to database
                        
                        # Notify all registered consumers
                        for callback in self.classification_consumers:
                            await callback(classification)
                            
                # Sleep a bit to avoid high CPU usage
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error consuming from {topic}: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
                
        if consumer:
            consumer.close()
            
    async def stop(self):
        """Stop all consumers"""
        self.running = False
        
        for task in self.consumer_tasks:
            task.cancel()
            
        # Wait for tasks to complete
        for task in self.consumer_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        self.consumer_tasks = []