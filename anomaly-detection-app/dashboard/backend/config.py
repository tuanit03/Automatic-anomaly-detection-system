import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "anomaly_detection")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092,kafka2:9092")
KAFKA_TOPIC_LOGS = os.getenv("KAFKA_TOPIC_LOGS", "logs")
KAFKA_TOPIC_CLASSIFICATIONS = os.getenv("KAFKA_TOPIC_CLASSIFICATIONS", "classifications")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "dashboard-backend")

# API configuration
API_PREFIX = "/api"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# CORS Configuration - Add more origins to ensure frontend can connect
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://frontend:80,http://localhost,http://localhost:80,http://127.0.0.1:3000")
CORS_ORIGINS = CORS_ORIGINS_STR.split(",")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

# Mock data generation
MOCK_DATA_ENABLED = os.getenv("MOCK_DATA_ENABLED", "True").lower() in ("true", "1", "t")
MOCK_DATA_INTERVAL_SECONDS = int(os.getenv("MOCK_DATA_INTERVAL_SECONDS", "5"))

# Slack configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SLACK_NOTIFICATION_ENABLED = os.getenv("SLACK_NOTIFICATION_ENABLED", "False").lower() in ("true", "1", "t")
SLACK_NOTIFICATION_INTERVAL_SECONDS = int(os.getenv("SLACK_NOTIFICATION_INTERVAL_SECONDS", "10"))