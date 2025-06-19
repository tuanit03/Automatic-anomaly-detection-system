# Anomaly Detection Kubernetes Manifests

## Tổng quan
Repository chứa các Kubernetes manifests để triển khai hệ thống Anomaly Detection Dashboard lên cluster K8s với kiến trúc microservices hoàn chỉnh.

## Cấu trúc thư mục

```
anomaly-detection-k8s/
├── kustomization.yaml          # Kustomize configuration
├── namespaces/                 # Namespace definitions
│   └── anomaly-system.yaml
└── applications/               # Application manifests
    ├── backend/                # FastAPI backend service
    ├── frontend/               # React frontend application  
    ├── kafka/                  # Kafka cluster (2 nodes + UI)
    └── timescaledb/           # TimescaleDB time-series database
```

## Thành phần hệ thống

### 🚀 Backend Service
- **Deployment**: FastAPI application với health checks
- **Image**: `registry.gitlab.com/natuan12a03/anomaly-detection-app/anomaly-backend`
- **Port**: 8000
- **Features**: Auto-scaling, secrets management, volume mounts
- **Config**: Environment variables từ ConfigMap & Secrets

### 🌐 Frontend Application  
- **Deployment**: React SPA với Nginx
- **Image**: `registry.gitlab.com/natuan12a03/anomaly-detection-app/anomaly-frontend`
- **Port**: 80
- **Ingress**: `anomaly-detection.local` với nginx-ingress
- **Routing**: Frontend (/) + API proxy (/api/)

### 📊 Kafka Cluster
- **Topology**: 2-node Kafka cluster (kafka1, kafka2)
- **Image**: `confluentinc/cp-kafka:7.8.0`
- **Features**: KRaft mode (no Zookeeper), persistent storage
- **UI**: Kafka-UI cho monitoring và management
- **Ports**: 9092, 9093 (internal), 9096 (external)

### 🗄️ TimescaleDB Database
- **Image**: `timescale/timescaledb:latest-pg14`
- **Port**: 5432
- **Storage**: Persistent volumes cho data persistence
- **Features**: Time-series optimization, PostgreSQL compatibility

## Configuration Management

### Secrets
- **backend-secrets**: Database credentials, Slack tokens
- **timescaledb-secret**: PostgreSQL passwords
- **gitlab-registry**: Container registry authentication

### ConfigMaps
- **backend-config**: Environment variables, feature flags
- **frontend-config**: API endpoints, build configurations
- **timescaledb-config**: Database initialization scripts

## Storage & Persistence

### Persistent Volumes
- **timescaledb-pv**: Database data storage (10Gi)
- **kafka-pv**: Kafka logs và metadata (5Gi each node)
- **backend-reports**: API test reports volume

## Network & Security

### Services
- **ClusterIP**: Internal communication giữa services
- **LoadBalancer**: External access cho frontend/backend
- **Headless**: Service discovery cho Kafka cluster

### Ingress Routing
```yaml
anomaly-detection.local/     → frontend:80
anomaly-detection.local/api/ → backend:8000
kafka-ui.anomaly-detection.local/ → kafka-ui:8080
```

## Monitoring & Health Checks

### Probes Configuration
- **Readiness**: Kiểm tra service ready nhận traffic
- **Liveness**: Restart container khi unhealthy
- **Startup**: Grace period cho slow starting services

### Resource Management
- **Requests**: Minimum resources cho scheduling
- **Limits**: Maximum resources để tránh resource starvation
- **HPA**: Horizontal Pod Autoscaler cho auto-scaling

## CI/CD Integration

Manifests được tự động cập nhật bởi GitLab CI pipeline:
1. **Image Tags**: Auto-update với commit SHA
2. **imagePullSecrets**: Tự động inject registry credentials  
3. **Rolling Updates**: Zero-downtime deployments
4. **Rollback**: Git-based rollback mechanism


## Architecture Benefits
- **Microservices**: Loosely coupled, independently scalable
- **Cloud Native**: Kubernetes-native patterns và best practices  
- **GitOps**: Infrastructure as Code với version control
- **Observability**: Comprehensive monitoring và logging
- **Security**: RBAC, secrets management, network policies