# Kubernetes Manifests

## Quick Deploy

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create secrets (replace with actual values!)
kubectl create secret generic deltastream-secrets \
  --from-literal=JWT_SECRET=your-secret-key-here \
  --namespace=deltastream

# Deploy infrastructure
kubectl apply -f redis-deployment.yaml
kubectl apply -f mongodb-deployment.yaml

# Wait for infrastructure
kubectl wait --for=condition=ready pod -l app=redis -n deltastream --timeout=120s
kubectl wait --for=condition=ready pod -l app=mongodb -n deltastream --timeout=120s

# Deploy services
kubectl apply -f api-gateway-deployment.yaml
kubectl apply -f worker-enricher-deployment.yaml
kubectl apply -f socket-gateway-deployment.yaml

# Check status
kubectl get pods -n deltastream
kubectl get services -n deltastream
```

## Scaling

```bash
# Scale workers
kubectl scale deployment worker-enricher --replicas=10 -n deltastream

# Scale API gateway
kubectl scale deployment api-gateway --replicas=5 -n deltastream
```

## Monitoring

```bash
# View logs
kubectl logs -f -l app=worker-enricher -n deltastream

# Check resource usage
kubectl top pods -n deltastream
```

## Cleanup

```bash
kubectl delete namespace deltastream
```
