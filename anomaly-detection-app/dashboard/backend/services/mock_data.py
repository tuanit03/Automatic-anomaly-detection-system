import asyncio
import random
import logging
from datetime import datetime
from typing import Callable, List
import ipaddress

import config
from models import LogEntryCreate, ClassificationCreate, AnomalyParamCreate

logger = logging.getLogger(__name__)

# Log level distribution for mock data
LOG_LEVELS = ["INFO", "WARNING", "ERROR", "CRITICAL"]
LOG_LEVEL_WEIGHTS = [0.9, 0.085, 0.01, 0.005]

# HDFS System Components
SYSTEM_COMPONENTS = [
    "dfs.FSNamesystem",
    "dfs.DataNode$PacketResponder",
    "dfs.DataNode$DataXceiver",
    "dfs.DataNode",
    "dfs.NameNode",
    "dfs.BlockManager",
    "dfs.FSDirectory",
    "dfs.StateChange"
]

# Helper function to generate random block IDs
def generate_block_id():
    return f"blk_{random.randint(1000000000000000000, 9999999999999999999)}"

# Helper function to generate random IP addresses
def generate_ip_address():
    return f"10.{random.randint(250, 251)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

# Helper function to generate random port
def generate_port():
    return random.choice([50010, 50075, 9000, 8020, 50070])

# Helper function to generate random block size
def generate_block_size():
    return random.choice([67108864, 134217728, 268435456])  # 64MB, 128MB, 256MB

# HDFS Log messages for each level
LOG_MESSAGES = {
    "INFO": [
        "BLOCK* NameSystem.addStoredBlock: blockMap updated: %s:%d is added to %s size %d",
        "PacketResponder %d for block %s terminating",
        "Received block %s of size %d from /%s",
        "Receiving block %s src: /%s:%d dest: /%s:%d",
        "BLOCK* NameSystem.allocateBlock: /%s. %s",
        "BLOCK* NameSystem.delete: %s is added to invalidSet of %s:%d",
        "STATE* Safe mode is OFF",
        "Verification succeeded for %s",
        "Successfully replicated %s. New replica count is %d"
    ],
    "WARNING": [
        "Low replica count for block %s: current replica count = %d",
        "Block %s has corrupt replica on %s:%d",
        "DataNode %s:%d is reaching disk capacity threshold"
    ],
    "ERROR": [
        "Failed to replicate block %s to %s:%d",
        "Block corruption detected for %s on %s:%d",
        "DataNode %s:%d failed to respond"
    ],
    "CRITICAL": [
        "NameNode entering safe mode due to corruption",
        "Severe block corruption detected: %s"
    ],
}

class MockDataGenerator:
    def __init__(self):
        self.running = False
        self.task = None
        self.log_callbacks = []
        self.classification_callbacks = []
        self.anomaly_param_callbacks = []
        
    def register_log_consumer(self, callback: Callable):
        """Register a callback for log messages"""
        self.log_callbacks.append(callback)
        
    def register_classification_consumer(self, callback: Callable):
        """Register a callback for classification messages"""
        self.classification_callbacks.append(callback)
        
    def register_anomaly_param_consumer(self, callback: Callable):
        """Register a callback for anomaly parameter messages"""
        self.anomaly_param_callbacks.append(callback)
        
    async def start(self):
        """Start generating mock data"""
        if self.running or not config.MOCK_DATA_ENABLED:
            return
            
        logger.info("Starting mock data generator")
        self.running = True
        self.task = asyncio.create_task(self._generate_data())
        
    async def stop(self):
        """Stop generating mock data"""
        if not self.running:
            return
            
        logger.info("Stopping mock data generator")
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
                
        self.task = None
        
    async def _generate_data(self):
        """Generate mock data at regular intervals"""
        try:
            while self.running:
                # Generate log entries
                await self._generate_log_entries()
                
                # Generate classification data
                await self._generate_classification_data()
                
                # Wait before generating more data
                await asyncio.sleep(config.MOCK_DATA_INTERVAL_SECONDS)
                
        except asyncio.CancelledError:
            logger.info("Mock data generation cancelled")
        except Exception as e:
            logger.error(f"Error in mock data generator: {str(e)}")
            
    async def _generate_log_entries(self):
        """Generate mock HDFS log entries"""
        # Generate 1-3 log entries per interval
        num_logs = random.randint(1, 3)
        
        for _ in range(num_logs):
            # Choose log level based on weights
            log_level = random.choices(LOG_LEVELS, weights=LOG_LEVEL_WEIGHTS)[0]
            
            # Select a message template for the chosen level
            message_template = random.choice(LOG_MESSAGES[log_level])
            
            # Generate HDFS-specific random values
            block_id = generate_block_id()
            ip_address = generate_ip_address()
            port = generate_port()
            block_size = generate_block_size()
            replica_count = random.randint(1, 4)
            packet_responder_id = random.randint(1, 10)
            file_path = f"/user/data/file_{random.randint(1000, 9999)}.log"
            
            # Fill in template placeholders with HDFS-specific values
            message = message_template
            
            # Replace placeholders based on message content and order
            if "PacketResponder" in message and "terminating" in message:
                message = message % (packet_responder_id, block_id)
            elif "Received block" in message and "of size" in message:
                message = message % (block_id, block_size, ip_address)
            elif "Receiving block" in message and "src:" in message:
                src_ip = generate_ip_address()
                src_port = random.randint(30000, 40000)
                dest_ip = generate_ip_address()
                dest_port = generate_port()
                message = message % (block_id, src_ip, src_port, dest_ip, dest_port)
            elif "addStoredBlock" in message:
                message = message % (ip_address, port, block_id, block_size)
            elif "allocateBlock" in message:
                message = message % (file_path, block_id)
            elif "delete" in message and "invalidSet" in message:
                message = message % (block_id, ip_address, port)
            elif "replica count" in message and "current" in message:
                message = message % (block_id, replica_count)
            elif "corrupt replica" in message:
                message = message % (block_id, ip_address, port)
            elif "disk capacity" in message:
                message = message % (ip_address, port)
            elif "Failed to replicate" in message:
                message = message % (block_id, ip_address, port)
            elif "Block corruption" in message:
                message = message % (block_id, ip_address, port)
            elif "failed to respond" in message:
                message = message % (ip_address, port)
            elif "Verification succeeded" in message:
                message = message % block_id
            elif "Successfully replicated" in message:
                message = message % (block_id, replica_count)
            elif "Severe block corruption" in message:
                message = message % block_id
            
            # Random HDFS component
            component = random.choice(SYSTEM_COMPONENTS)
            
            # Create HDFS log message format (without timestamp as it's handled elsewhere)
            final_message = f"{component}: {message}"
            
            log_entry = LogEntryCreate(
                message=final_message,
                log_level=log_level,
            )
            
            # Notify callbacks
            for callback in self.log_callbacks:
                await callback(log_entry)
                
    async def _generate_classification_data(self):
        """Generate mock classification data"""
        # Generate classification counts
        # Most data should be normal, with occasional anomalies
        total_events = random.randint(1, 50)
        anomaly_percent = random.uniform(0.001, 0.03)  
        unidentified_percent = random.uniform(0.001, 0.02) 
        
        anomaly_count = int(total_events * anomaly_percent)
        unidentified_count = int(total_events * unidentified_percent)
        normal_count = total_events - anomaly_count - unidentified_count
        
        # Create classification object
        classification = ClassificationCreate(
            normal_count=normal_count,
            anomaly_count=anomaly_count,
            unidentified_count=unidentified_count
        )
        
        # Notify callbacks
        for callback in self.classification_callbacks:
            await callback(classification)
            
        # Generate anomaly parameters if there are anomalies
        if anomaly_count > 0:
            # Generate 1-3 anomaly parameters
            num_params = min(3, anomaly_count)
            
            for _ in range(num_params):
                # Generate HDFS-specific anomalies
                block_id = generate_block_id()
                ip_address = generate_ip_address()
                port = generate_port()
                
                param_values = [
                    f"Block replication failure: {block_id} on DataNode {ip_address}:{port}",
                    f"NameNode heap memory critical: {random.randint(85, 98)}% used",
                    f"DataNode disk usage warning: {ip_address}:{port} at {random.randint(80, 95)}% capacity",
                    f"Block corruption detected: {block_id} has {random.randint(2, 5)} corrupt replicas",
                    f"HDFS safe mode activated: {random.randint(5, 15)} under-replicated blocks",
                    f"DataNode heartbeat timeout: {ip_address}:{port} unresponsive for {random.randint(30, 120)}s"
                ]
                
                anomaly_param = AnomalyParamCreate(
                    param_value=random.choice(param_values),
                    classification_type="anomaly"
                )
                
                # Call the anomaly parameter callbacks
                for callback in self.anomaly_param_callbacks:
                    await callback(anomaly_param)
                
        # Generate unidentified parameters if there are unidentified events
        if unidentified_count > 0:
            # Generate 1-3 unidentified parameters
            num_params = min(3, unidentified_count)
            
            for _ in range(num_params):
                # Generate HDFS unidentified issues
                block_id = generate_block_id()
                ip_address = generate_ip_address()
                port = generate_port()
                
                param_values = [
                    f"Unknown block state: {block_id} status inconsistent across DataNodes",
                    f"Unusual network pattern: {ip_address}:{port} unexpected traffic spike",
                    f"Metadata inconsistency detected: block {block_id} location mismatch",
                    f"Unexpected DataNode behavior: {ip_address}:{port} reporting anomalous metrics",
                    f"HDFS namespace anomaly: unknown file system operation pattern"
                ]
                
                unidentified_param = AnomalyParamCreate(
                    param_value=random.choice(param_values),
                    classification_type="unidentified"
                )
                
                # Call the anomaly parameter callbacks
                for callback in self.anomaly_param_callbacks:
                    await callback(unidentified_param)