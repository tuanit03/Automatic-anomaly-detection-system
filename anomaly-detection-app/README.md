# Anomaly Detection Dashboard

## Tổng quan
Hệ thống dashboard phát hiện bất thường với kiến trúc microservices, bao gồm backend FastAPI, frontend React, và tích hợp Kafka + TimescaleDB để xử lý dữ liệu streaming real-time.

## Kiến trúc hệ thống

### Backend (FastAPI)
- **API Server**: FastAPI với async/await support
- **Database**: TimescaleDB với SQLAlchemy ORM
- **Message Queue**: Kafka Consumer để xử lý log streaming
- **Notification**: Slack integration cho cảnh báo
- **Mock Data**: Service tạo dữ liệu test

### Frontend (React)
- **Framework**: React 19 với Material-UI
- **Charts**: Recharts cho visualization
- **Testing**: Jest + React Testing Library
- **HTTP Client**: Axios

### Infrastructure
- **Containerization**: Docker với multi-stage builds
- **Orchestration**: Kubernetes deployment
- **CI/CD**: GitLab CI với optimized image building
- **Storage**: TimescaleDB cho time-series data

## Tính năng chính

### Dashboard 4 Quadrants
1. **Real-time Logs**: Theo dõi Kafka logs trực tiếp
2. **Statistics Counter**: Thống kê normal/anomaly/unidentified
3. **Anomaly List**: Danh sách param_values bất thường
4. **Time Series Chart**: Biểu đồ xu hướng theo thời gian

### API Endpoints
- `/api/logs/stream` - SSE real-time logs
- `/api/statistics` - Thống kê tổng quan
- `/api/anomalies` - Danh sách bất thường
- `/api/test-reports` - Báo cáo kiểm thử
- `/api/slack` - Tích hợp thông báo

## CI/CD Pipeline

### Optimized Build Process
- **Smart Image Checking**: Kiểm tra image tồn tại trước khi build
- **Change Detection**: Chỉ build khi có thay đổi code
- **Parallel Testing**: Backend (pytest) và Frontend (jest) song song
- **Multi-stage Docker**: Tối ưu kích thước image
- **Auto Deployment**: Cập nhật K8s manifests tự động

### Pipeline Stages
1. **Prepare**: Check existing images và detect changes
2. **Test**: Unit tests với coverage reports
3. **Build**: Docker images với caching
4. **Deploy**: Update Kubernetes manifests

## Deployment

### Local Development
```bash
# Start với Docker Compose
docker-compose up -d

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Kafka UI: http://localhost:8080
```

### Production (Kubernetes)
- **Namespace**: anomaly-system
- **Registry**: GitLab Container Registry
- **Ingress**: Nginx với TLS
- **Secrets**: Database credentials + API keys

## Monitoring & Observability
- **Health Checks**: Liveness/Readiness probes
- **Logging**: Structured logging với log levels
- **Metrics**: Database connection pooling
- **Alerting**: Slack notifications cho anomalies