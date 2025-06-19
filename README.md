# Hướng dẫn Triển khai Anomaly Detection trên Kubernetes

## Tổng quan
Tài liệu này mô tả chi tiết từng bước để triển khai hệ thống Anomaly Detection lên Kubernetes cluster, bao gồm application deployment, monitoring tools, và GitOps với ArgoCD.

## Giai đoạn 1: Kiểm tra và Chuẩn bị Cluster

### 1.1 Kiểm tra trạng thái cluster
```bash
# Kiểm tra các nodes trong cluster
kubectl get nodes
```
**Mục đích**: Xác minh cluster đang hoạt động và có đủ nodes để deploy

```bash
# Xem context hiện tại
kubectl config current-context
```
**Mục đích**: Đảm bảo đang kết nối đúng cluster (local/cloud)

### 1.2 Tạo namespace cho ứng dụng
```bash
# Tạo namespace riêng cho hệ thống
kubectl create namespace anomaly-system
```
**Mục đích**: Tạo namespace isolation cho các resources của dự án

```bash
# Xác minh namespace đã được tạo
kubectl get namespaces | grep anomaly-system
```
**Kết quả mong đợi**: Hiển thị `anomaly-system` trong danh sách

## Giai đoạn 2: Cấu hình Registry Access

### 2.1 Tạo secret cho GitLab Container Registry
```bash
kubectl create secret docker-registry gitlab-registry \
  --docker-server=registry.gitlab.com \
  --docker-username=<YOUR_USERNAME> \
  --docker-password=<YOUR_GITLAB_TOKEN> \
  --docker-email=<YOUR_EMAIL> \
  -n anomaly-system
```
**Mục đích**: 
- Cho phép Kubernetes pull images từ private GitLab registry
- **Thay thế**: `<YOUR_USERNAME>`, `<YOUR_GITLAB_TOKEN>`, `<YOUR_EMAIL>` bằng thông tin thực

### 2.2 Xác minh secret
```bash
# Kiểm tra secret đã tạo thành công
kubectl get secrets -n anomaly-system
```
**Kết quả mong đợi**: Thấy `gitlab-registry` trong danh sách secrets

## Giai đoạn 3: Deploy Ứng dụng Chính

### 3.1 Clone repository manifests
```bash
# Di chuyển về home directory
cd ~

# Clone repository chứa Kubernetes manifests
git clone https://gitlab.com/natuan12a03/anomaly-detection-k8s.git

# Di chuyển vào thư mục project
cd anomaly-detection-k8s
```
**Mục đích**: Tải về các file YAML định nghĩa infrastructure

### 3.2 Deploy toàn bộ hệ thống
```bash
# Apply tất cả manifests sử dụng Kustomize
kubectl apply -k .
```
**Mục đích**: 
- Deploy: Backend, Frontend, Kafka cluster, TimescaleDB
- Tạo: Services, ConfigMaps, Secrets, PersistentVolumes
- **Kustomize** tự động resolve dependencies giữa các resources

## Giai đoạn 4: Cài đặt Ingress Controller

### 4.1 Deploy NGINX Ingress Controller
```bash
# Cài đặt NGINX Ingress từ official manifests
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
```
**Mục đích**: Cung cấp external access cho frontend và API

### 4.2 Chờ Ingress Controller sẵn sàng
```bash
# Chờ controller pods ready (timeout 120s)
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```
**Mục đích**: Đảm bảo ingress controller hoạt động trước khi test

## Giai đoạn 5: Kiểm tra Deployment

### 5.1 Kiểm tra pods
```bash
# Xem trạng thái tất cả pods
kubectl get pods -n anomaly-system
```
**Kết quả mong đợi**: Tất cả pods ở trạng thái `Running` hoặc `Ready`

```bash
# Xem chi tiết pods (troubleshooting)
kubectl describe pods -n anomaly-system
```
**Mục đích**: Debug nếu có pods failed/pending

### 5.2 Kiểm tra services
```bash
# Liệt kê services và endpoints
kubectl get svc -n anomaly-system
```
**Kết quả mong đợi**: 
- backend: ClusterIP:8000
- frontend: ClusterIP:80
- kafka-service: ClusterIP:9092
- timescaledb: ClusterIP:5432

### 5.3 Kiểm tra storage
```bash
# Kiểm tra Persistent Volume Claims
kubectl get pvc -n anomaly-system
```
**Mục đích**: Xác minh storage đã được bind cho database

### 5.4 Kiểm tra ingress
```bash
# Xem ingress rules và endpoints
kubectl get ingress -n anomaly-system
```
**Kết quả mong đợi**: Ingress có external IP/hostname

## Giai đoạn 6: Cài đặt Kubernetes Dashboard (Optional)

### 6.1 Cài đặt Dashboard qua Helm
```bash
# Thêm Helm repository
helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/

# Cài đặt dashboard
helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard --create-namespace --namespace kubernetes-dashboard
```
**Mục đích**: Web UI để quản lý cluster trực quan

### 6.2 Tạo admin user
```bash
# Tạo service account
kubectl create serviceaccount admin-user -n kubernetes-dashboard

# Gán cluster admin role
kubectl create clusterrolebinding admin-user-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=kubernetes-dashboard:admin-user
```

### 6.3 Lấy access token
```bash
# Generate token để login dashboard
kubectl -n kubernetes-dashboard create token admin-user
```
**Lưu ý**: Copy token này để login vào dashboard

### 6.4 Truy cập Dashboard
```bash
# Port forward dashboard service
kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 8443:443
```
**Truy cập**: https://localhost:8443 (sử dụng token ở bước 6.3)

## Giai đoạn 7: Cài đặt ArgoCD (GitOps)

### 7.1 Deploy ArgoCD
```bash
# Tạo namespace cho ArgoCD
kubectl create namespace argocd

# Cài đặt ArgoCD components
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 7.2 Chờ ArgoCD khởi động
```bash
# Kiểm tra pods ArgoCD
kubectl get pods -n argocd
```
**Chờ**: Tất cả pods `Running` trước khi tiếp tục

### 7.3 Cấu hình GitLab repository
```bash
# Tạo secret cho repository access
kubectl create secret generic gitlab-repo-secret \
  --from-literal=type=git \
  --from-literal=url=https://gitlab.com/<YOUR_USERNAME>/anomaly-detection-k8s.git \
  --from-literal=username=<YOUR_USERNAME> \
  --from-literal=password=<YOUR_GITLAB_TOKEN> \
  -n argocd

# Label secret để ArgoCD nhận diện
kubectl label secret gitlab-repo-secret argocd.argoproj.io/secret-type=repository -n argocd
```
**Thay thế**: Credentials của bạn

### 7.4 Deploy ArgoCD Application
```bash
# Apply application manifest
kubectl apply -f argocd-application.yaml
```
**Mục đích**: Tạo ArgoCD app để sync từ Git repository

### 7.5 Kiểm tra ArgoCD
```bash
# Xem applications
kubectl get applications -n argocd

# Check controller logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
```

### 7.6 Truy cập ArgoCD UI
```bash
# Port forward ArgoCD server
kubectl port-forward svc/argocd-server -n argocd 8080:443 &

# Lấy admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```
**Truy cập**: https://localhost:8080
- **Username**: admin  
- **Password**: Output từ command trên

## Giai đoạn 8: Testing và Port Forwarding

### 8.1 Direct access tới services
```bash
# Port forward backend service
kubectl port-forward svc/backend 8000:8000 -n anomaly-system &

# Port forward frontend service  
kubectl port-forward svc/frontend 3000:80 -n anomaly-system &
```
**Mục đích**: Test direct access bypassing ingress

### 8.2 Kiểm tra port forwards
```bash
# Xem các process port-forward đang chạy
ps aux | grep "kubectl port-forward"
```

## URLs Truy cập

### Production (qua Ingress)
- **Frontend Dashboard**: http://anomaly-detection.local
- **Backend API**: http://anomaly-detection.local/api  
- **Kafka UI**: http://kafka-ui.anomaly-detection.local

### Development (Port Forward)
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Kubernetes Dashboard**: https://localhost:8443
- **ArgoCD**: https://localhost:8080

## Troubleshooting Common Issues

### 1. Pods không start
```bash
kubectl describe pod <pod-name> -n anomaly-system
kubectl logs <pod-name> -n anomaly-system
```

### 2. Image pull errors
```bash
kubectl get events -n anomaly-system --sort-by='.lastTimestamp'
```

### 3. Storage issues
```bash
kubectl get pv
kubectl describe pvc <pvc-name> -n anomaly-system
```

### 4. Ingress không hoạt động
```bash
kubectl get ingress -A
kubectl describe ingress <ingress-name> -n anomaly-system
```

## Cleanup Commands

```bash
# Xóa toàn bộ application
kubectl delete namespace anomaly-system

# Xóa ArgoCD
kubectl delete namespace argocd

# Xóa Kubernetes Dashboard
kubectl delete namespace kubernetes-dashboard

# Xóa NGINX Ingress
kubectl delete -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
```
