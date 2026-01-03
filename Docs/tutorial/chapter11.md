## Part 11: Kubernetes Deployment

### Learning Objectives

By the end of Part 11, you will understand:

1. **Kubernetes architecture** - Pods, Deployments, Services
2. **Resource management** - CPU/memory requests and limits
3. **Health checks** - Liveness and readiness probes
4. **Scaling** - Horizontal pod autoscaling
5. **ConfigMaps & Secrets** - Configuration management
6. **Service discovery** - DNS-based service names

---

### 11.1 Kubernetes Architecture

**Kubernetes components:**

```
┌────────────────────────────────────────┐
│           Kubernetes Cluster           │
│                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────┐│
│  │  Pod 1   │  │  Pod 2   │  │ Pod 3││
│  │ Gateway  │  │ Worker   │  │Socket││
│  └──────────┘  └──────────┘  └──────┘│
│       ▲             ▲            ▲    │
│       │             │            │    │
│  ┌────────────────────────────────┐  │
│  │         Service (LB)           │  │
│  └────────────────────────────────┘  │
└────────────────────────────────────────┘
```

**Key concepts:**
- **Pod**: Smallest deployable unit (1+ containers)
- **Deployment**: Manages pod replicas
- **Service**: Load balancer for pods
- **ConfigMap**: Configuration data
- **Secret**: Sensitive data (encrypted)

---

### 11.2 Namespace

`k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deltastream
```

**Why namespaces?**
- Logical isolation
- Resource quotas
- Access control
- Multiple environments (dev, staging, prod)

---

### 11.3 Secrets

`k8s/secrets-example.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: deltastream-secrets
  namespace: deltastream
type: Opaque
stringData:
  JWT_SECRET: "your-secret-key-here"
  HUGGINGFACE_API_TOKEN: "hf_xxxxxxxxxxxxx"
```

**Create secret:**
```bash
kubectl create secret generic deltastream-secrets \
  --from-literal=JWT_SECRET=abc123 \
  --from-literal=HUGGINGFACE_API_TOKEN= hf_xxx \
  --namespace=deltastream
```

---

### 11.4 API Gateway Deployment

`k8s/api-gateway-deployment.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-gateway-config
  namespace: deltastream
data:
  AUTH_SERVICE_URL: "http://auth:8001"
  STORAGE_SERVICE_URL: "http://storage:8003"
  ANALYTICS_SERVICE_URL: "http://analytics:8004"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: deltastream
spec:
  replicas: 3  # 3 instances for HA
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: deltastream/api-gateway:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: api-gateway-config
        - secretRef:
            name: deltastream-secrets
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: deltastream
spec:
  selector:
    app: api-gateway
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

**Key features:**

**1. Resource limits:**
```yaml
resources:
  requests:    # Minimum guaranteed
    memory: "128Mi"
    cpu: "100m"
  limits:      # Maximum allowed
    memory: "256Mi"
    cpu: "200m"
```

**2. Health probes:**
```yaml
livenessProbe:   # Is container alive?
  httpGet:
    path: /health
    port: 8000
  periodSeconds: 30

readinessProbe:  # Is container ready for traffic?
  httpGet:
    path: /health
    port: 8000
  periodSeconds: 10
```

**Liveness vs Readiness:**
- **Liveness**: Fails → Kubernetes restarts pod
- **Readiness**: Fails → Kubernetes stops sending traffic (but doesn't restart)

---

### 11.5 Deploying to Kubernetes

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create secrets
kubectl create secret generic deltastream-secrets \
  --from-literal=JWT_SECRET=$(openssl rand -hex 32) \
  --namespace=deltastream

# 3. Deploy infrastructure
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/mongodb-deployment.yaml

# 4. Wait for infrastructure
kubectl wait --for=condition=ready pod -l app=redis \
  -n deltastream --timeout=120s

# 5. Deploy services
kubectl apply -f k8s/api-gateway-deployment.yaml
kubectl apply -f k8s/worker-enricher-deployment.yaml
kubectl apply -f k8s/socket-gateway-deployment.yaml

# 6. Check status
kubectl get pods -n deltastream
kubectl get services -n deltastream

# 7. View logs
kubectl logs -f -l app=api-gateway -n deltastream

# 8. Scale
kubectl scale deployment api-gateway --replicas=5 -n deltastream
```

---

### 11.6 Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: deltastream
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**How it works:**
- CPU > 70% → scale up (add pods)
- CPU < 70% → scale down (remove pods)
- Min: 2 pods, Max: 10 pods

---

