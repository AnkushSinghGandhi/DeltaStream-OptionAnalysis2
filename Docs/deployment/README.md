# Deployment Documentation

> **Guides for deploying DeltaStream to various environments**

## 📚 Contents

### [Docker Compose Deployment](docker-compose.md)
Local and development deployment using Docker Compose

### [Kubernetes Deployment](kubernetes.md)
Production deployment on Kubernetes
- Namespace setup
- Deployments and Services
- ConfigMaps and Secrets
- Horizontal Pod Autoscaling

### [Observability Setup](observability.md)
Monitoring and logging infrastructure
- Prometheus for metrics
- Grafana for visualization
- Loki for log aggregation

### [Verification Guide](verification.md)
How to verify your deployment is working correctly

---

## 🚀 Quick Start

**Local Development:**
```bash
docker-compose up -d
```

**Production (Kubernetes):**
```bash
kubectl apply -f k8s/
```

---

*Follow these guides to deploy DeltaStream in your environment.*
