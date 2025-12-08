# Kubernetes Manifests

## Quick Deploy

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create secrets (replace with actual values!)
kubectl create secret generic option-aro-secrets \
  --from-literal=JWT_SECRET=your-secret-key-here \
  --namespace=option-aro

# Deploy infrastructure
kubectl apply -f redis-deployment.yaml
kubectl apply -f mongodb-deployment.yaml

# Wait for infrastructure
kubectl wait --for=condition=ready pod -l app=redis -n option-aro --timeout=120s
kubectl wait --for=condition=ready pod -l app=mongodb -n option-aro --timeout=120s

# Deploy services
kubectl apply -f api-gateway-deployment.yaml
kubectl apply -f worker-enricher-deployment.yaml
kubectl apply -f socket-gateway-deployment.yaml

# Check status
kubectl get pods -n option-aro
kubectl get services -n option-aro
```

## Scaling

```bash
# Scale workers
kubectl scale deployment worker-enricher --replicas=10 -n option-aro

# Scale API gateway
kubectl scale deployment api-gateway --replicas=5 -n option-aro
```

## Monitoring

```bash
# View logs
kubectl logs -f -l app=worker-enricher -n option-aro

# Check resource usage
kubectl top pods -n option-aro
```

## Cleanup

```bash
kubectl delete namespace option-aro
```
