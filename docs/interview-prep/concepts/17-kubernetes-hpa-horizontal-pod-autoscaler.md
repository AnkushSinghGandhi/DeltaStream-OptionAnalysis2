### **17. KUBERNETES HPA (Horizontal Pod Autoscaler)**

**What it is:**
Kubernetes feature that automatically scales number of pods based on CPU/memory usage.

**In your manifest:**
```yaml
spec:
  minReplicas: 2        # Never fewer than 2
  maxReplicas: 10       # Never more than 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70  # Scale up if CPU > 70%
```

**How it works:**
```
Normal load: 2 replicas running
↓
Load increases, CPU hits 75%
↓
HPA creates 1 more replica (now 3 total)
↓
Load increases further, CPU still high
↓
HPA creates more replicas (up to 10 max)
↓
Load decreases, CPU drops below 70%
↓
HPA removes replicas (down to 2 min)
```

**Why HPA:**
- **Cost efficiency**: Pay only for what you need
- **Automatic**: No manual intervention
- **Handles spikes**: Black swan events, market crashes → auto-scale

---
