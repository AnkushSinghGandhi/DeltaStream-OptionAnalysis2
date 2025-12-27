# DeltaStream - Option Analysis - Complete Tutorial

A comprehensive guide to understanding microservices architecture, real-time data processing, and modern DevOps practices through the DeltaStream trading analytics platform.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Tools & Technologies](#3-tools--technologies)
4. [Infrastructure Deep Dive](#4-infrastructure-deep-dive)
   - [Docker](#41-docker)
   - [Docker Compose](#42-docker-compose)
   - [Kubernetes (K8s)](#43-kubernetes-k8s)
   - [Redis](#44-redis)
   - [MongoDB](#45-mongodb)
5. [Microservices Explained](#5-microservices-explained)
   - [Feed Generator](#51-feed-generator)
   - [Worker Enricher (Celery)](#52-worker-enricher-celery)
   - [Socket Gateway (Flask-SocketIO)](#53-socket-gateway-flask-socketio)
   - [API Gateway](#54-api-gateway)
   - [Storage Service](#55-storage-service)
   - [Auth Service](#56-auth-service)
   - [Analytics Service](#57-analytics-service)
   - [Logging Service](#58-logging-service)
6. [Communication Patterns](#6-communication-patterns)
   - [Redis Pub/Sub](#61-redis-pubsub)
   - [WebSocket Communication](#62-websocket-communication)
   - [REST API](#63-rest-api)
7. [Caching Strategies](#7-caching-strategies)
8. [Message Queuing with Celery](#8-message-queuing-with-celery)
9. [Observability & Monitoring](#9-observability--monitoring)
10. [CI/CD Pipeline](#10-cicd-pipeline)
11. [Security Best Practices](#11-security-best-practices)
12. [Scaling Strategies](#12-scaling-strategies)
13. [Interview Questions & Answers](#13-interview-questions--answers)
14. [Hands-On Exercises](#14-hands-on-exercises)
15. [Troubleshooting Guide](#15-troubleshooting-guide)

---

## 1. Introduction

### What is DeltaStream?

DeltaStream is a real-time option trading analytics platform that provides:
- Live market data streaming
- Option chain analysis
- Put-Call Ratio (PCR) calculations
- Implied Volatility (IV) surface
- Max Pain analysis
- Open Interest build-up tracking

### What You'll Learn

This tutorial teaches you:
- **Microservices Architecture**: How to design and build distributed systems
- **Real-time Data Processing**: Stream processing with Redis and WebSockets
- **Container Orchestration**: Docker and Kubernetes fundamentals
- **Message Queuing**: Celery for distributed task processing
- **Caching Strategies**: Redis for high-performance caching
- **API Design**: RESTful APIs with Flask
- **DevOps Practices**: CI/CD, monitoring, and logging

### Prerequisites

- Basic Python knowledge
- Familiarity with command line
- Docker installed on your machine
- 4GB+ RAM available

---

## 2. Architecture Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DELTASTREAM ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                      ┌─────────────────┐               │
│  │  Feed Generator │──────publish────────▶│  Redis Pub/Sub  │               │
│  │  (Data Source)  │                      │  (Message Bus)  │               │
│  └─────────────────┘                      └────────┬────────┘               │
│                                                    │                         │
│                                           subscribe│                         │
│                                                    ▼                         │
│                                           ┌─────────────────┐               │
│                                           │ Worker Enricher │               │
│                                           │    (Celery)     │               │
│                                           └────────┬────────┘               │
│                                                    │                         │
│                          ┌─────────────────────────┼─────────────────────┐  │
│                          │                         │                     │  │
│                          ▼                         ▼                     ▼  │
│                 ┌─────────────────┐       ┌─────────────────┐   ┌──────────┐│
│                 │    MongoDB      │       │  Redis Cache    │   │  Pub/Sub ││
│                 │  (Persistence)  │       │   (TTL Data)    │   │(enriched)││
│                 └─────────────────┘       └─────────────────┘   └────┬─────┘│
│                          ▲                         ▲                 │      │
│                          │                         │                 │      │
│                 ┌────────┴─────────────────────────┴────┐           │      │
│                 │           Storage Service             │           │      │
│                 │         (Data Access Layer)           │           │      │
│                 └────────────────┬──────────────────────┘           │      │
│                                  │                                   │      │
│                                  ▼                                   ▼      │
│  ┌─────────────────┐    ┌─────────────────┐              ┌─────────────────┐│
│  │   Auth Service  │◀───│   API Gateway   │              │ Socket Gateway  ││
│  │     (JWT)       │    │   (REST API)    │              │(Flask-SocketIO) ││
│  └─────────────────┘    └────────┬────────┘              └────────┬────────┘│
│                                  │                                 │        │
│                                  │                                 │        │
│                                  ▼                                 ▼        │
│                         ┌───────────────────────────────────────────┐       │
│                         │              CLIENTS                      │       │
│                         │   (Web Browser, Mobile App, Node.js)      │       │
│                         └───────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Feed Generator** creates synthetic market data
2. **Redis Pub/Sub** distributes messages to subscribers
3. **Worker Enricher** processes and calculates metrics
4. **MongoDB** stores historical data
5. **Redis Cache** stores latest values with TTL
6. **Socket Gateway** broadcasts to WebSocket clients
7. **API Gateway** serves REST requests

---

## 3. Tools & Technologies

### Why Each Tool Was Chosen

| Tool | Purpose | Why Chosen |
|------|---------|------------|
| **Python** | Backend services | Simple, readable, rich ecosystem |
| **Flask** | Web framework | Lightweight, flexible, easy to learn |
| **Flask-SocketIO** | WebSockets | Native Flask integration, room support |
| **Celery** | Task queue | Distributed, reliable, Python-native |
| **Redis** | Cache & broker | Fast, versatile, pub/sub support |
| **MongoDB** | Database | Flexible schema, JSON-like documents |
| **Docker** | Containerization | Consistent environments, easy deployment |
| **Kubernetes** | Orchestration | Scalability, self-healing, production-grade |
| **Prometheus** | Metrics | Time-series, pull-based, industry standard |
| **Grafana** | Visualization | Beautiful dashboards, alerting |

### Tool Comparison Matrix

```
┌─────────────────┬───────────────────┬──────────────────┬─────────────────┐
│ Category        │ Our Choice        │ Alternative 1    │ Alternative 2   │
├─────────────────┼───────────────────┼──────────────────┼─────────────────┤
│ Message Broker  │ Redis             │ RabbitMQ         │ Apache Kafka    │
│ Database        │ MongoDB           │ PostgreSQL       │ Cassandra       │
│ Task Queue      │ Celery            │ RQ (Redis Queue) │ Dramatiq        │
│ WebSocket       │ Flask-SocketIO    │ FastAPI WebSocket│ Tornado         │
│ API Framework   │ Flask             │ FastAPI          │ Django          │
│ Container       │ Docker            │ Podman           │ containerd      │
│ Orchestration   │ Kubernetes        │ Docker Swarm     │ Nomad           │
└─────────────────┴───────────────────┴──────────────────┴─────────────────┘
```

---

## 4. Infrastructure Deep Dive

### 4.1 Docker

#### What is Docker?

Docker is a platform for developing, shipping, and running applications in **containers**. Containers are lightweight, standalone, executable packages that include everything needed to run software.

#### Key Concepts

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCKER CONCEPTS                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    build     ┌─────────────┐              │
│  │  Dockerfile │ ──────────▶  │    Image    │              │
│  │  (Recipe)   │              │  (Template) │              │
│  └─────────────┘              └──────┬──────┘              │
│                                      │                      │
│                                      │ run                  │
│                                      ▼                      │
│                               ┌─────────────┐              │
│                               │  Container  │              │
│                               │ (Instance)  │              │
│                               └─────────────┘              │
│                                                             │
│  Dockerfile = Blueprint (instructions to build image)       │
│  Image = Snapshot (built, immutable template)               │
│  Container = Running instance (live, modifiable)            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Our Dockerfile Example

```dockerfile
# services/api-gateway/Dockerfile

# Base image - Python 3.11 slim variant (smaller size)
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose port (documentation, not actual port binding)
EXPOSE 8000

# Command to run when container starts
CMD ["python", "app.py"]
```

#### Dockerfile Best Practices

```dockerfile
# ❌ BAD: Copies everything, breaks caching
COPY . .
RUN pip install -r requirements.txt

# ✅ GOOD: Separate dependency installation from code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# ❌ BAD: Uses root user
USER root

# ✅ GOOD: Creates non-root user
RUN useradd -m appuser
USER appuser

# ❌ BAD: Multiple RUN commands
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*

# ✅ GOOD: Single RUN with cleanup
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*
```

#### Docker Commands Tutorial

```bash
# ============================================
# BASIC DOCKER COMMANDS
# ============================================

# Build an image from Dockerfile
docker build -t my-app:latest .

# List all images
docker images

# Run a container
docker run -d -p 8000:8000 --name my-container my-app:latest
#   -d = detached (background)
#   -p = port mapping (host:container)
#   --name = container name

# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View container logs
docker logs my-container
docker logs -f my-container  # Follow logs in real-time

# Execute command inside container
docker exec -it my-container /bin/bash
#   -i = interactive
#   -t = allocate TTY (terminal)

# Stop container
docker stop my-container

# Remove container
docker rm my-container

# Remove image
docker rmi my-app:latest

# ============================================
# ADVANCED DOCKER COMMANDS
# ============================================

# Build with build arguments
docker build --build-arg VERSION=1.0 -t my-app:1.0 .

# Run with environment variables
docker run -e DATABASE_URL=mongodb://... my-app

# Run with volume mount (persist data)
docker run -v /host/path:/container/path my-app

# Run with network
docker run --network my-network my-app

# View resource usage
docker stats

# Clean up unused resources
docker system prune -a
```

---

### 4.2 Docker Compose

#### What is Docker Compose?

Docker Compose is a tool for defining and running **multi-container** Docker applications. You use a YAML file to configure your services, networks, and volumes.

#### Our docker-compose.yml Explained

```yaml
# docker-compose.yml

version: '3.8'  # Compose file format version

services:
  # ============================================
  # INFRASTRUCTURE SERVICES
  # ============================================
  
  redis:
    image: redis:7-alpine          # Official Redis image (Alpine = smaller)
    container_name: deltastream-redis
    ports:
      - "6379:6379"                # Expose Redis port
    command: redis-server --appendonly yes  # Enable persistence
    volumes:
      - redis_data:/data           # Persist data to named volume
    networks:
      - deltastream-network         # Connect to custom network
    healthcheck:                   # Health check configuration
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s                 # Check every 5 seconds
      timeout: 3s                  # Timeout after 3 seconds
      retries: 5                   # Retry 5 times before unhealthy

  mongodb:
    image: mongo:6
    container_name: deltastream-mongodb
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: deltastream  # Create database on startup
    volumes:
      - mongo_data:/data/db
    networks:
      - deltastream-network
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/deltastream --quiet
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================
  # APPLICATION SERVICES
  # ============================================
  
  api-gateway:
    build:
      context: ./services/api-gateway  # Build from this directory
      dockerfile: Dockerfile           # Using this Dockerfile
    container_name: deltastream-api-gateway
    ports:
      - "8000:8000"
    environment:                       # Environment variables
      - REDIS_URL=redis://redis:6379/0
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - AUTH_SERVICE_URL=http://auth:8001
      - STORAGE_SERVICE_URL=http://storage:8003
      - ANALYTICS_SERVICE_URL=http://analytics:8004
      - SERVICE_NAME=api-gateway
    depends_on:                        # Start these services first
      - redis
      - mongodb
      - auth
    networks:
      - deltastream-network
    restart: unless-stopped            # Restart policy

  worker-enricher:
    build:
      context: ./services/worker-enricher
      dockerfile: Dockerfile
    container_name: deltastream-worker
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MONGO_URL=mongodb://mongodb:27017/deltastream
      - CELERY_BROKER_URL=redis://redis:6379/1   # Separate Redis DB for Celery
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
      - SERVICE_NAME=worker-enricher
    depends_on:
      redis:
        condition: service_healthy     # Wait until Redis is healthy
      mongodb:
        condition: service_healthy
    networks:
      - deltastream-network
    restart: unless-stopped

# ============================================
# VOLUMES (Persistent Storage)
# ============================================
volumes:
  redis_data:    # Named volume for Redis data
  mongo_data:    # Named volume for MongoDB data

# ============================================
# NETWORKS (Container Communication)
# ============================================
networks:
  deltastream-network:
    driver: bridge  # Default network driver
```

#### Docker Compose Commands

```bash
# ============================================
# DOCKER COMPOSE COMMANDS
# ============================================

# Start all services
docker-compose up -d
#   -d = detached mode (background)

# Start specific service
docker-compose up -d api-gateway

# Build and start (rebuild images)
docker-compose up -d --build

# Stop all services
docker-compose down

# Stop and remove volumes (DELETE ALL DATA!)
docker-compose down -v

# View logs
docker-compose logs
docker-compose logs -f              # Follow logs
docker-compose logs -f api-gateway  # Specific service

# Scale a service (run multiple instances)
docker-compose up -d --scale worker-enricher=3

# Execute command in running service
docker-compose exec redis redis-cli
docker-compose exec mongodb mongosh deltastream

# View running services
docker-compose ps

# Restart a service
docker-compose restart api-gateway

# Pull latest images
docker-compose pull

# View service configuration
docker-compose config
```

---

### 4.3 Kubernetes (K8s)

#### What is Kubernetes?

Kubernetes (K8s) is an open-source **container orchestration platform** that automates deploying, scaling, and managing containerized applications.

#### Why Kubernetes?

```
┌─────────────────────────────────────────────────────────────┐
│                 WHY KUBERNETES?                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Problem                    │  Kubernetes Solution          │
│  ──────────────────────────┼───────────────────────────────│
│  Manual container mgmt     │  Automated orchestration       │
│  Service discovery         │  Built-in DNS & load balancing│
│  Scaling                   │  Auto-scaling (HPA)           │
│  Self-healing              │  Automatic restart/replace    │
│  Rolling updates           │  Zero-downtime deployments    │
│  Configuration mgmt        │  ConfigMaps & Secrets         │
│  Storage orchestration     │  Persistent Volumes           │
│  Resource management       │  CPU/Memory limits & requests │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Kubernetes Core Concepts

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    KUBERNETES ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     CONTROL PLANE (Master)                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐│   │
│  │  │ API Server  │  │ Scheduler   │  │ Controller  │  │  etcd   ││   │
│  │  │             │  │             │  │  Manager    │  │ (store) ││   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      WORKER NODES                                │   │
│  │                                                                   │   │
│  │  ┌─────────────────────────┐    ┌─────────────────────────┐     │   │
│  │  │       NODE 1            │    │       NODE 2            │     │   │
│  │  │  ┌─────────────────┐   │    │  ┌─────────────────┐   │     │   │
│  │  │  │      POD        │   │    │  │      POD        │   │     │   │
│  │  │  │  ┌───────────┐  │   │    │  │  ┌───────────┐  │   │     │   │
│  │  │  │  │ Container │  │   │    │  │  │ Container │  │   │     │   │
│  │  │  │  └───────────┘  │   │    │  │  └───────────┘  │   │     │   │
│  │  │  └─────────────────┘   │    │  └─────────────────┘   │     │   │
│  │  │  ┌─────────┐ ┌───────┐ │    │  ┌─────────┐ ┌───────┐ │     │   │
│  │  │  │ Kubelet │ │ Proxy │ │    │  │ Kubelet │ │ Proxy │ │     │   │
│  │  │  └─────────┘ └───────┘ │    │  └─────────┘ └───────┘ │     │   │
│  │  └─────────────────────────┘    └─────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

KEY CONCEPTS:
─────────────
• Pod: Smallest deployable unit (1+ containers)
• Deployment: Manages Pod replicas & updates
• Service: Stable network endpoint for Pods
• ConfigMap: Non-sensitive configuration
• Secret: Sensitive data (passwords, keys)
• Namespace: Virtual cluster isolation
• Ingress: External HTTP/HTTPS routing
```

#### Our Kubernetes Manifests Explained

**1. Namespace (k8s/namespace.yaml)**

```yaml
# Namespace creates an isolated environment for our application
apiVersion: v1
kind: Namespace
metadata:
  name: deltastream           # All our resources will be in this namespace
  labels:
    app: deltastream
    environment: production
```

**2. Secrets (k8s/secrets-example.yaml)**

```yaml
# Secrets store sensitive data (base64 encoded)
apiVersion: v1
kind: Secret
metadata:
  name: deltastream-secrets
  namespace: deltastream
type: Opaque
data:
  # Values are base64 encoded
  # echo -n 'your-secret-key' | base64
  jwt-secret: eW91ci1zZWNyZXQta2V5LWNoYW5nZS1pbi1wcm9kdWN0aW9u
  mongo-password: bW9uZ29wYXNzd29yZA==
  
# How to create secrets from command line:
# kubectl create secret generic my-secret \
#   --from-literal=password=mypassword \
#   --namespace=deltastream
```

**3. ConfigMap (for non-sensitive config)**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deltastream-config
  namespace: deltastream
data:
  REDIS_URL: "redis://redis-service:6379/0"
  MONGO_URL: "mongodb://mongodb-service:27017/deltastream"
  LOG_LEVEL: "INFO"
  FEED_INTERVAL: "1"
```

**4. Deployment (k8s/api-gateway-deployment.yaml)**

```yaml
# Deployment manages the lifecycle of Pods
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: deltastream
  labels:
    app: api-gateway
spec:
  replicas: 2                    # Run 2 instances for high availability
  
  selector:
    matchLabels:
      app: api-gateway           # Select pods with this label
  
  strategy:
    type: RollingUpdate          # Update strategy
    rollingUpdate:
      maxUnavailable: 1          # Max pods that can be unavailable during update
      maxSurge: 1                # Max pods that can be created above desired
  
  template:                      # Pod template
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
        - name: api-gateway
          image: deltastream/api-gateway:latest
          
          ports:
            - containerPort: 8000
          
          # Environment variables
          env:
            - name: SERVICE_NAME
              value: "api-gateway"
            - name: REDIS_URL
              valueFrom:
                configMapKeyRef:
                  name: deltastream-config
                  key: REDIS_URL
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: deltastream-secrets
                  key: jwt-secret
          
          # Resource limits
          resources:
            requests:              # Minimum resources guaranteed
              memory: "128Mi"
              cpu: "100m"         # 100 millicores = 0.1 CPU
            limits:               # Maximum resources allowed
              memory: "256Mi"
              cpu: "500m"
          
          # Health checks
          livenessProbe:          # Is the container alive?
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          
          readinessProbe:         # Is the container ready to serve traffic?
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5

---
# Service exposes the Deployment
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: deltastream
spec:
  selector:
    app: api-gateway             # Route traffic to pods with this label
  ports:
    - port: 8000                 # Service port
      targetPort: 8000           # Container port
  type: ClusterIP                # Internal only (use LoadBalancer for external)
```

**5. Worker Deployment with Horizontal Pod Autoscaler**

```yaml
# k8s/worker-enricher-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-enricher
  namespace: deltastream
spec:
  replicas: 2
  selector:
    matchLabels:
      app: worker-enricher
  template:
    metadata:
      labels:
        app: worker-enricher
    spec:
      containers:
        - name: worker
          image: deltastream/worker-enricher:latest
          env:
            - name: CELERY_BROKER_URL
              value: "redis://redis-service:6379/1"
          resources:
            requests:
              memory: "256Mi"
              cpu: "200m"
            limits:
              memory: "512Mi"
              cpu: "1000m"

---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: worker-enricher-hpa
  namespace: deltastream
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: worker-enricher
  minReplicas: 2                 # Minimum pods
  maxReplicas: 10                # Maximum pods
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70  # Scale when CPU > 70%
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

**6. Ingress (External Access)**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: deltastream-ingress
  namespace: deltastream
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"  # For HTTPS
spec:
  tls:
    - hosts:
        - api.deltastream.com
      secretName: deltastream-tls
  rules:
    - host: api.deltastream.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-gateway-service
                port:
                  number: 8000
          - path: /ws
            pathType: Prefix
            backend:
              service:
                name: socket-gateway-service
                port:
                  number: 8002
```

#### Kubernetes Commands Tutorial

```bash
# ============================================
# KUBECTL BASICS
# ============================================

# Check kubectl version and cluster info
kubectl version
kubectl cluster-info

# ============================================
# NAMESPACE OPERATIONS
# ============================================

# Create namespace
kubectl create namespace deltastream

# List namespaces
kubectl get namespaces

# Set default namespace for context
kubectl config set-context --current --namespace=deltastream

# ============================================
# APPLYING MANIFESTS
# ============================================

# Apply single file
kubectl apply -f k8s/namespace.yaml

# Apply all files in directory
kubectl apply -f k8s/

# Apply with dry-run (preview changes)
kubectl apply -f k8s/ --dry-run=client

# Delete resources
kubectl delete -f k8s/api-gateway-deployment.yaml

# ============================================
# VIEWING RESOURCES
# ============================================

# Get all resources in namespace
kubectl get all -n option-aro

# Get specific resource types
kubectl get pods -n option-aro
kubectl get deployments -n option-aro
kubectl get services -n option-aro
kubectl get configmaps -n option-aro
kubectl get secrets -n option-aro

# Detailed view
kubectl get pods -o wide -n option-aro

# Watch for changes (live updates)
kubectl get pods -w -n option-aro

# ============================================
# DESCRIBING RESOURCES (Debugging)
# ============================================

# Describe a pod (shows events, status, etc.)
kubectl describe pod api-gateway-abc123 -n option-aro

# Describe a deployment
kubectl describe deployment api-gateway -n option-aro

# ============================================
# LOGS
# ============================================

# View pod logs
kubectl logs api-gateway-abc123 -n option-aro

# Follow logs (real-time)
kubectl logs -f api-gateway-abc123 -n option-aro

# Logs from all pods with label
kubectl logs -l app=api-gateway -n option-aro

# Previous container logs (if crashed)
kubectl logs api-gateway-abc123 --previous -n option-aro

# ============================================
# EXECUTING COMMANDS IN PODS
# ============================================

# Open shell in pod
kubectl exec -it api-gateway-abc123 -n option-aro -- /bin/sh

# Run single command
kubectl exec api-gateway-abc123 -n option-aro -- ls -la

# ============================================
# SCALING
# ============================================

# Scale deployment manually
kubectl scale deployment worker-enricher --replicas=5 -n option-aro

# Check HPA status
kubectl get hpa -n option-aro

# ============================================
# ROLLING UPDATES
# ============================================

# Update image
kubectl set image deployment/api-gateway api-gateway=option-aro/api-gateway:v2 -n option-aro

# Check rollout status
kubectl rollout status deployment/api-gateway -n option-aro

# View rollout history
kubectl rollout history deployment/api-gateway -n option-aro

# Rollback to previous version
kubectl rollout undo deployment/api-gateway -n option-aro

# Rollback to specific revision
kubectl rollout undo deployment/api-gateway --to-revision=2 -n option-aro

# ============================================
# PORT FORWARDING (Local Testing)
# ============================================

# Forward local port to pod
kubectl port-forward pod/api-gateway-abc123 8000:8000 -n option-aro

# Forward to service
kubectl port-forward svc/api-gateway-service 8000:8000 -n option-aro

# ============================================
# RESOURCE MANAGEMENT
# ============================================

# Check resource usage
kubectl top pods -n option-aro
kubectl top nodes

# ============================================
# DEBUGGING
# ============================================

# Get events (useful for debugging)
kubectl get events -n option-aro --sort-by='.lastTimestamp'

# Check pod status
kubectl get pods -n option-aro -o jsonpath='{.items[*].status.phase}'

# Debug with temporary pod
kubectl run debug --rm -it --image=busybox -n option-aro -- sh
```

#### Kubernetes vs Docker Compose Comparison

```
┌─────────────────┬─────────────────────┬────────────────────────────┐
│ Feature         │ Docker Compose      │ Kubernetes                 │
├─────────────────┼─────────────────────┼────────────────────────────┤
│ Use Case        │ Development, simple │ Production, complex apps   │
│ Scaling         │ Manual              │ Auto-scaling (HPA)         │
│ Self-healing    │ restart: always     │ Automatic pod replacement  │
│ Load Balancing  │ Manual/external     │ Built-in Service LB        │
│ Rolling Updates │ Manual              │ Built-in, zero-downtime    │
│ Service Mesh    │ No                  │ Istio, Linkerd support     │
│ Multi-host      │ Swarm mode only     │ Native multi-node          │
│ Complexity      │ Low                 │ High                       │
│ Learning Curve  │ Easy                │ Steep                      │
└─────────────────┴─────────────────────┴────────────────────────────┘
```

---

### 4.4 Redis

#### What is Redis?

Redis is an in-memory data structure store used as:
- **Database**: Key-value store
- **Cache**: Fast data access layer
- **Message Broker**: Pub/Sub messaging

#### Redis Data Structures

```
┌─────────────────────────────────────────────────────────────┐
│                  REDIS DATA STRUCTURES                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STRING: Simple key-value                                   │
│  ─────────────────────                                      │
│  SET price:NIFTY "21500.50"                                │
│  GET price:NIFTY  →  "21500.50"                            │
│                                                             │
│  HASH: Object-like structure                                │
│  ──────────────────────────                                 │
│  HSET user:1 name "John" email "john@email.com"            │
│  HGET user:1 name  →  "John"                               │
│  HGETALL user:1  →  {name: "John", email: "john@..."}      │
│                                                             │
│  LIST: Ordered collection                                   │
│  ───────────────────────                                    │
│  LPUSH queue:tasks "task1"                                 │
│  RPOP queue:tasks  →  "task1"                              │
│                                                             │
│  SET: Unique unordered collection                           │
│  ─────────────────────────────                              │
│  SADD products "NIFTY" "BANKNIFTY"                         │
│  SMEMBERS products  →  ["NIFTY", "BANKNIFTY"]              │
│                                                             │
│  SORTED SET: Ordered by score                               │
│  ───────────────────────────                                │
│  ZADD leaderboard 100 "user1" 200 "user2"                  │
│  ZRANGE leaderboard 0 -1 WITHSCORES                        │
│                                                             │
│  PUB/SUB: Messaging                                         │
│  ─────────────────                                          │
│  PUBLISH channel:market "price update"                     │
│  SUBSCRIBE channel:market                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### How We Use Redis

```python
# services/worker-enricher/app.py

import redis
import json

# Connect to Redis
redis_client = redis.from_url('redis://localhost:6379/0', decode_responses=True)

# ============================================
# 1. CACHING (with TTL)
# ============================================

def cache_latest_price(product: str, price: float):
    """
    Cache the latest price with 5-minute expiry.
    
    Why TTL (Time-To-Live)?
    - Prevents stale data
    - Automatic cleanup
    - Memory management
    """
    key = f"latest:underlying:{product}"
    value = json.dumps({
        'price': price,
        'timestamp': datetime.now().isoformat()
    })
    
    # SETEX: SET with EXpiry (in seconds)
    redis_client.setex(key, 300, value)  # 300 seconds = 5 minutes

def get_cached_price(product: str):
    """Get cached price if exists."""
    key = f"latest:underlying:{product}"
    cached = redis_client.get(key)
    
    if cached:
        return json.loads(cached)
    return None

# ============================================
# 2. PUBLISH/SUBSCRIBE
# ============================================

def publish_market_data(channel: str, data: dict):
    """
    Publish data to a channel.
    
    Use case: Broadcast real-time updates to all subscribers.
    """
    redis_client.publish(channel, json.dumps(data))

def subscribe_to_market_data():
    """
    Subscribe to market data channels.
    
    This creates a blocking listener that receives all published messages.
    """
    pubsub = redis_client.pubsub()
    
    # Subscribe to multiple channels
    pubsub.subscribe('market:underlying', 'market:option_chain')
    
    # Listen for messages
    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel']
            data = json.loads(message['data'])
            
            # Process message based on channel
            if channel == 'market:underlying':
                process_underlying_tick(data)
            elif channel == 'market:option_chain':
                process_option_chain(data)

# ============================================
# 3. IDEMPOTENCY CHECK
# ============================================

def is_already_processed(tick_id: str) -> bool:
    """
    Check if a tick was already processed (prevent duplicates).
    
    Pattern: Use Redis SET with NX (only set if Not eXists)
    """
    key = f"processed:tick:{tick_id}"
    
    # SETNX returns True if key was set (not exists)
    # Returns False if key already exists
    was_set = redis_client.setnx(key, '1')
    
    if was_set:
        # Set expiry to clean up old keys
        redis_client.expire(key, 3600)  # 1 hour
        return False  # Not processed before
    
    return True  # Already processed

# ============================================
# 4. DEAD LETTER QUEUE (DLQ)
# ============================================

def send_to_dlq(task_data: dict, error: str):
    """
    Send failed tasks to Dead Letter Queue for later analysis.
    
    Why DLQ?
    - Don't lose failed messages
    - Debug and replay later
    - Monitor failure patterns
    """
    dlq_entry = {
        'task': task_data,
        'error': error,
        'timestamp': datetime.now().isoformat()
    }
    
    # LPUSH: Add to left (front) of list
    redis_client.lpush('dlq:enrichment', json.dumps(dlq_entry))

def get_dlq_messages(count: int = 10):
    """Get messages from DLQ for debugging."""
    # LRANGE: Get range of elements
    messages = redis_client.lrange('dlq:enrichment', 0, count - 1)
    return [json.loads(m) for m in messages]
```

#### Redis CLI Commands

```bash
# Connect to Redis CLI
redis-cli

# Or with Docker
docker-compose exec redis redis-cli

# ============================================
# BASIC COMMANDS
# ============================================

# Set a key
SET mykey "Hello"

# Get a key
GET mykey

# Set with expiry (seconds)
SETEX tempkey 60 "I will expire in 60 seconds"

# Check TTL (Time To Live)
TTL tempkey

# Delete a key
DEL mykey

# Check if key exists
EXISTS mykey

# Get all keys matching pattern
KEYS "latest:*"

# ============================================
# PUB/SUB COMMANDS
# ============================================

# Subscribe to a channel (in one terminal)
SUBSCRIBE market:underlying

# Publish to a channel (in another terminal)
PUBLISH market:underlying '{"product":"NIFTY","price":21500}'

# Subscribe to multiple channels
PSUBSCRIBE market:*

# ============================================
# MONITORING
# ============================================

# Monitor all commands (debugging)
MONITOR

# Get server info
INFO

# Get memory usage
INFO memory

# Get number of connected clients
CLIENT LIST
```

---

### 4.5 MongoDB

#### What is MongoDB?

MongoDB is a **document-oriented NoSQL database** that stores data in flexible, JSON-like documents (BSON).

#### Why MongoDB?

```
┌─────────────────────────────────────────────────────────────┐
│              MONGODB vs SQL DATABASES                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SQL (PostgreSQL)           │  MongoDB                      │
│  ─────────────────────────────────────────────────────────  │
│  Table                      │  Collection                   │
│  Row                        │  Document                     │
│  Column                     │  Field                        │
│  Schema (rigid)             │  Schema (flexible)            │
│  JOIN                       │  Embedded documents/$lookup   │
│                                                             │
│  ADVANTAGES OF MONGODB:                                     │
│  ✓ Flexible schema - add fields without migrations          │
│  ✓ JSON-like documents - natural for APIs                   │
│  ✓ Horizontal scaling - sharding built-in                   │
│  ✓ Fast reads - with proper indexing                        │
│  ✓ Rich query language                                      │
│                                                             │
│  WHEN TO USE SQL INSTEAD:                                   │
│  ✓ Complex transactions (ACID)                              │
│  ✓ Many-to-many relationships                               │
│  ✓ Strict data integrity required                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Document Structure Example

```javascript
// Option chain document in MongoDB
{
  "_id": ObjectId("65abc123..."),      // Auto-generated unique ID
  "product": "NIFTY",
  "expiry": "2025-01-25",
  "spot_price": 21543.25,
  "timestamp": ISODate("2025-01-15T10:30:00Z"),
  
  // Embedded documents (denormalized)
  "calls": [
    {
      "strike": 21500,
      "bid": 125.50,
      "ask": 126.25,
      "volume": 5000,
      "open_interest": 150000,
      "iv": 0.18
    },
    {
      "strike": 21600,
      "bid": 85.25,
      "ask": 86.00,
      "volume": 3000,
      "open_interest": 120000,
      "iv": 0.19
    }
  ],
  
  "puts": [
    {
      "strike": 21500,
      "bid": 118.75,
      "ask": 119.50,
      "volume": 4500,
      "open_interest": 145000,
      "iv": 0.17
    }
  ],
  
  // Computed fields
  "pcr_oi": 1.0234,
  "pcr_volume": 0.9876,
  "atm_strike": 21500,
  "atm_straddle_price": 244.25,
  "max_pain_strike": 21400,
  
  // Metadata
  "processed_at": ISODate("2025-01-15T10:30:01Z")
}
```

#### How We Use MongoDB

```python
# services/storage/app.py

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timedelta

# Connect to MongoDB
mongo_client = MongoClient('mongodb://localhost:27017/option_aro')
db = mongo_client['option_aro']

# ============================================
# 1. CREATE INDEXES (Performance Critical!)
# ============================================

def setup_indexes():
    """
    Create indexes for common query patterns.
    
    Why indexes?
    - Without index: Full collection scan (slow)
    - With index: Direct lookup (fast)
    
    Rule: Index fields used in queries and sorts
    """
    # Compound index for queries like: 
    # "Get NIFTY ticks sorted by time"
    db.underlying_ticks.create_index([
        ('product', ASCENDING),
        ('timestamp', DESCENDING)
    ])
    
    # Single field index
    db.underlying_ticks.create_index([('timestamp', DESCENDING)])
    
    # Compound for option chains
    db.option_chains.create_index([
        ('product', ASCENDING),
        ('expiry', ASCENDING),
        ('timestamp', DESCENDING)
    ])
    
    # Unique index (prevents duplicates)
    db.users.create_index('email', unique=True)

# ============================================
# 2. INSERT OPERATIONS
# ============================================

def insert_tick(tick_data: dict):
    """Insert a single tick."""
    result = db.underlying_ticks.insert_one({
        'product': tick_data['product'],
        'price': tick_data['price'],
        'timestamp': datetime.fromisoformat(tick_data['timestamp']),
        'tick_id': tick_data['tick_id'],
        'processed_at': datetime.now()
    })
    return str(result.inserted_id)

def insert_many_ticks(ticks: list):
    """Insert multiple ticks (bulk operation)."""
    result = db.underlying_ticks.insert_many(ticks)
    return len(result.inserted_ids)

# ============================================
# 3. QUERY OPERATIONS
# ============================================

def get_underlying_ticks(product: str, limit: int = 100):
    """
    Get recent ticks for a product.
    
    Query pattern: Filter + Sort + Limit
    """
    ticks = list(db.underlying_ticks.find(
        {'product': product},           # Filter
        {'_id': 0}                       # Projection (exclude _id)
    ).sort('timestamp', DESCENDING)     # Sort
     .limit(limit))                      # Limit
    
    return ticks

def get_ticks_in_range(product: str, start: datetime, end: datetime):
    """
    Get ticks within a time range.
    
    Uses range query with $gte (>=) and $lte (<=)
    """
    query = {
        'product': product,
        'timestamp': {
            '$gte': start,
            '$lte': end
        }
    }
    
    return list(db.underlying_ticks.find(query, {'_id': 0}))

def get_latest_chain(product: str, expiry: str = None):
    """
    Get the most recent option chain.
    
    Uses find_one with sort for "latest" pattern
    """
    query = {'product': product}
    if expiry:
        query['expiry'] = expiry
    
    chain = db.option_chains.find_one(
        query,
        sort=[('timestamp', DESCENDING)]  # Get latest
    )
    
    return chain

# ============================================
# 4. AGGREGATION PIPELINE
# ============================================

def get_ohlc(product: str, interval_minutes: int = 5):
    """
    Calculate OHLC using aggregation pipeline.
    
    Aggregation stages:
    $match -> $group -> $sort -> $project
    """
    start_time = datetime.now() - timedelta(hours=1)
    
    pipeline = [
        # Stage 1: Filter documents
        {
            '$match': {
                'product': product,
                'timestamp': {'$gte': start_time}
            }
        },
        # Stage 2: Group by time interval
        {
            '$group': {
                '_id': {
                    '$dateTrunc': {
                        'date': '$timestamp',
                        'unit': 'minute',
                        'binSize': interval_minutes
                    }
                },
                'open': {'$first': '$price'},   # First price in interval
                'high': {'$max': '$price'},     # Highest price
                'low': {'$min': '$price'},      # Lowest price
                'close': {'$last': '$price'},   # Last price
                'count': {'$sum': 1}            # Number of ticks
            }
        },
        # Stage 3: Sort by time
        {
            '$sort': {'_id': DESCENDING}
        },
        # Stage 4: Reshape output
        {
            '$project': {
                '_id': 0,
                'interval_start': '$_id',
                'open': 1,
                'high': 1,
                'low': 1,
                'close': 1,
                'count': 1
            }
        }
    ]
    
    return list(db.underlying_ticks.aggregate(pipeline))

def get_pcr_trend(product: str, hours: int = 24):
    """Get PCR trend over time using aggregation."""
    start_time = datetime.now() - timedelta(hours=hours)
    
    pipeline = [
        {'$match': {'product': product, 'timestamp': {'$gte': start_time}}},
        {'$project': {
            'timestamp': 1,
            'pcr_oi': 1,
            'pcr_volume': 1,
            'expiry': 1
        }},
        {'$sort': {'timestamp': ASCENDING}}
    ]
    
    return list(db.option_chains.aggregate(pipeline))

# ============================================
# 5. UPDATE OPERATIONS
# ============================================

def update_user_profile(user_id: str, updates: dict):
    """
    Update a document.
    
    $set: Update specific fields without affecting others
    """
    result = db.users.update_one(
        {'_id': ObjectId(user_id)},
        {
            '$set': {
                **updates,
                'updated_at': datetime.now()
            }
        }
    )
    return result.modified_count

def upsert_latest_price(product: str, price: float):
    """
    Update if exists, insert if not (upsert).
    
    Useful for maintaining "latest" documents
    """
    result = db.latest_prices.update_one(
        {'product': product},
        {
            '$set': {
                'price': price,
                'updated_at': datetime.now()
            }
        },
        upsert=True  # Insert if not exists
    )
    return result.upserted_id or result.modified_count
```

#### MongoDB Shell Commands

```javascript
// Connect to MongoDB shell
// mongosh option_aro

// ============================================
// DATABASE OPERATIONS
// ============================================

// Show all databases
show dbs

// Use database
use option_aro

// Show collections
show collections

// ============================================
// QUERY EXAMPLES
// ============================================

// Find all documents
db.underlying_ticks.find()

// Find with filter
db.underlying_ticks.find({product: "NIFTY"})

// Find one (latest)
db.option_chains.findOne(
  {product: "NIFTY"},
  {sort: {timestamp: -1}}
)

// Find with projection (select fields)
db.underlying_ticks.find(
  {product: "NIFTY"},
  {price: 1, timestamp: 1, _id: 0}
)

// Count documents
db.underlying_ticks.countDocuments({product: "NIFTY"})

// Distinct values
db.option_chains.distinct("expiry", {product: "NIFTY"})

// ============================================
// INDEX OPERATIONS
// ============================================

// List indexes
db.underlying_ticks.getIndexes()

// Create index
db.underlying_ticks.createIndex({product: 1, timestamp: -1})

// Explain query (see if index is used)
db.underlying_ticks.find({product: "NIFTY"}).explain("executionStats")

// ============================================
// AGGREGATION EXAMPLES
// ============================================

// Count by product
db.underlying_ticks.aggregate([
  {$group: {_id: "$product", count: {$sum: 1}}},
  {$sort: {count: -1}}
])

// Average price by product
db.underlying_ticks.aggregate([
  {$group: {
    _id: "$product",
    avgPrice: {$avg: "$price"},
    minPrice: {$min: "$price"},
    maxPrice: {$max: "$price"}
  }}
])

// ============================================
// ADMIN OPERATIONS
// ============================================

// Database stats
db.stats()

// Collection stats
db.underlying_ticks.stats()

// Server status
db.serverStatus()
```

---

## 5. Microservices Explained

### 5.1 Feed Generator

#### Purpose
Generates realistic synthetic option market data for testing and demonstration.

#### How It Works

```python
# services/feed-generator/app.py

"""
FEED GENERATOR FLOW:
====================

1. Initialize with base prices for products
2. Loop forever:
   a. For each product:
      - Update underlying price (random walk)
      - Generate option chain (calls + puts)
      - Calculate Greeks (delta, gamma, vega, theta)
      - Publish to Redis pub/sub
   b. Sleep for interval
"""

class OptionFeedGenerator:
    """
    Generates realistic option market data.
    
    Key concepts implemented:
    - Geometric Brownian Motion for price simulation
    - Black-Scholes approximation for option pricing
    - Greeks calculation
    - Bid-ask spread simulation
    """
    
    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL)
        self.current_prices = {
            'NIFTY': 21500,
            'BANKNIFTY': 45000,
            'AAPL': 185,
            'TSLA': 245
        }
    
    def update_underlying_price(self, product: str):
        """
        Simulate price movement using random walk.
        
        Geometric Brownian Motion (simplified):
        new_price = old_price * (1 + random_change)
        
        Where random_change follows normal distribution
        with mean=0 and std=volatility
        """
        current = self.current_prices[product]
        
        # Volatility varies by product type
        volatility = 0.0002 if product in ['NIFTY', 'SENSEX'] else 0.0005
        
        # Random percentage change
        change_pct = random.gauss(0, volatility)
        
        # Apply change
        new_price = current * (1 + change_pct)
        
        self.current_prices[product] = round(new_price, 2)
    
    def calculate_option_price(self, spot, strike, option_type, tte, iv):
        """
        Simplified Black-Scholes approximation.
        
        Real Black-Scholes formula:
        Call = S*N(d1) - K*e^(-rT)*N(d2)
        Put  = K*e^(-rT)*N(-d2) - S*N(-d1)
        
        Where:
        d1 = (ln(S/K) + (r + σ²/2)T) / (σ√T)
        d2 = d1 - σ√T
        N() = cumulative normal distribution
        
        For demo, we use simplified approximation.
        """
        # Intrinsic value
        if option_type == 'CALL':
            intrinsic = max(0, spot - strike)
        else:
            intrinsic = max(0, strike - spot)
        
        # Time value (simplified)
        time_value = spot * iv * math.sqrt(tte) * 0.4
        
        return intrinsic + time_value
    
    def generate_option_chain(self, product: str, expiry: str):
        """
        Generate complete option chain with all strikes.
        
        Option Chain Structure:
        ┌─────────┬────────────────────┬────────────────────┐
        │ Strike  │     CALL           │      PUT           │
        ├─────────┼────────────────────┼────────────────────┤
        │ 21400   │ Bid/Ask/Vol/OI/IV  │ Bid/Ask/Vol/OI/IV  │
        │ 21450   │ Bid/Ask/Vol/OI/IV  │ Bid/Ask/Vol/OI/IV  │
        │ 21500   │ Bid/Ask/Vol/OI/IV  │ Bid/Ask/Vol/OI/IV  │ ← ATM
        │ 21550   │ Bid/Ask/Vol/OI/IV  │ Bid/Ask/Vol/OI/IV  │
        │ 21600   │ Bid/Ask/Vol/OI/IV  │ Bid/Ask/Vol/OI/IV  │
        └─────────┴────────────────────┴────────────────────┘
        """
        spot = self.current_prices[product]
        strikes = self.generate_strikes(spot)
        
        calls = []
        puts = []
        
        for strike in strikes:
            call = self.generate_option_quote(spot, strike, expiry, 'CALL')
            put = self.generate_option_quote(spot, strike, expiry, 'PUT')
            calls.append(call)
            puts.append(put)
        
        return {
            'product': product,
            'expiry': expiry,
            'spot_price': spot,
            'strikes': strikes,
            'calls': calls,
            'puts': puts,
            'timestamp': datetime.now().isoformat()
        }
    
    def publish_tick(self, product: str):
        """Publish market data to Redis channels."""
        
        # Update price
        self.update_underlying_price(product)
        
        # Publish underlying tick
        underlying_tick = {
            'type': 'UNDERLYING',
            'product': product,
            'price': self.current_prices[product],
            'timestamp': datetime.now().isoformat()
        }
        self.redis_client.publish('market:underlying', json.dumps(underlying_tick))
        
        # Publish option chain (every 5 ticks)
        if self.tick_count % 5 == 0:
            chain = self.generate_option_chain(product, self.nearest_expiry)
            self.redis_client.publish('market:option_chain', json.dumps(chain))
    
    def run(self):
        """Main loop - generates data continuously."""
        while True:
            for product in ['NIFTY', 'BANKNIFTY', 'AAPL', 'TSLA']:
                self.publish_tick(product)
            
            time.sleep(FEED_INTERVAL)  # Default: 1 second
```

---

### 5.2 Worker Enricher (Celery)

#### What is Celery?

Celery is a **distributed task queue** that allows you to run tasks asynchronously (in background) across multiple workers.

#### Why Celery?

```
┌─────────────────────────────────────────────────────────────┐
│                  CELERY BENEFITS                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  WITHOUT CELERY (Synchronous):                              │
│  ──────────────────────────────                             │
│  Request → Process → Response                               │
│  User waits while processing happens (slow!)                │
│                                                             │
│  WITH CELERY (Asynchronous):                                │
│  ───────────────────────────                                │
│  Request → Queue Task → Response (immediate)                │
│           ↓                                                 │
│        Worker processes in background                       │
│                                                             │
│  FEATURES:                                                  │
│  ✓ Distributed - multiple workers                          │
│  ✓ Reliable - task persistence, retries                    │
│  ✓ Scalable - add more workers as needed                   │
│  ✓ Scheduled tasks (celerybeat)                            │
│  ✓ Result backend - store task results                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Celery Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CELERY ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────────┐ │
│  │  Producer   │─────▶│   Broker    │─────▶│    Worker(s)    │ │
│  │ (your app)  │      │   (Redis)   │      │ (Celery process)│ │
│  └─────────────┘      └─────────────┘      └────────┬────────┘ │
│                                                      │          │
│                                                      ▼          │
│                                             ┌─────────────────┐ │
│                                             │ Result Backend  │ │
│                                             │    (Redis)      │ │
│                                             └─────────────────┘ │
│                                                                 │
│  FLOW:                                                          │
│  1. Producer creates task and sends to Broker                   │
│  2. Broker stores task in queue                                 │
│  3. Worker picks up task from queue                             │
│  4. Worker executes task                                        │
│  5. Worker stores result in Result Backend (optional)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Our Worker Implementation

```python
# services/worker-enricher/app.py

from celery import Celery, Task
from pymongo import MongoClient
import redis

# ============================================
# CELERY CONFIGURATION
# ============================================

celery_app = Celery(
    'worker-enricher',
    broker='redis://localhost:6379/1',      # Task queue
    backend='redis://localhost:6379/2'       # Results storage
)

celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Reliability settings
    task_track_started=True,        # Track when task starts
    task_acks_late=True,            # Ack after task completes (not before)
    worker_prefetch_multiplier=1,   # One task at a time
    task_reject_on_worker_lost=True,# Reject if worker dies
    
    # Retry configuration
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3, 'countdown': 5},
)

# ============================================
# CUSTOM TASK BASE CLASS
# ============================================

class EnrichmentTask(Task):
    """
    Custom task base class with error handling.
    
    Implements:
    - Failure logging
    - Dead-letter queue for failed tasks
    """
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails after all retries."""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Send to dead-letter queue
        dlq_entry = {
            'task_id': task_id,
            'task_name': self.name,
            'error': str(exc),
            'args': args,
            'timestamp': datetime.now().isoformat()
        }
        redis_client.lpush('dlq:enrichment', json.dumps(dlq_entry))

# ============================================
# CELERY TASKS
# ============================================

@celery_app.task(base=EnrichmentTask, bind=True)
def process_underlying_tick(self, tick_data: dict):
    """
    Process underlying price tick.
    
    @celery_app.task: Decorator to register as Celery task
    base=EnrichmentTask: Use custom base class
    bind=True: First argument is task instance (self)
    
    Steps:
    1. Idempotency check (skip if already processed)
    2. Store in MongoDB
    3. Update Redis cache
    4. Trigger OHLC calculations
    5. Publish enriched event
    """
    product = tick_data['product']
    tick_id = tick_data.get('tick_id', 0)
    
    # Step 1: Idempotency check
    idempotency_key = f"processed:underlying:{product}:{tick_id}"
    if redis_client.exists(idempotency_key):
        logger.info(f"Tick {tick_id} already processed, skipping")
        return
    
    # Step 2: Store in MongoDB
    db = get_mongo_client()['option_aro']
    db.underlying_ticks.insert_one({
        'product': product,
        'price': tick_data['price'],
        'timestamp': datetime.fromisoformat(tick_data['timestamp']),
        'tick_id': tick_id,
        'processed_at': datetime.now()
    })
    
    # Step 3: Update Redis cache (5 min TTL)
    redis_client.setex(
        f"latest:underlying:{product}",
        300,
        json.dumps({
            'price': tick_data['price'],
            'timestamp': tick_data['timestamp']
        })
    )
    
    # Step 4: Trigger OHLC calculations
    for window in [1, 5, 15]:
        calculate_ohlc_window.delay(product, window)  # .delay() = async call
    
    # Step 5: Mark as processed & publish
    redis_client.setex(idempotency_key, 3600, '1')
    
    enriched = {
        'type': 'UNDERLYING_ENRICHED',
        'product': product,
        'price': tick_data['price'],
        'timestamp': tick_data['timestamp'],
        'processed_at': datetime.now().isoformat()
    }
    redis_client.publish('enriched:underlying', json.dumps(enriched))

@celery_app.task(base=EnrichmentTask, bind=True)
def process_option_chain(self, chain_data: dict):
    """
    Process and enrich option chain data.
    
    Enrichment calculations:
    1. PCR (Put-Call Ratio)
    2. ATM straddle price
    3. Max pain strike
    4. OI build-up analysis
    """
    product = chain_data['product']
    calls = chain_data['calls']
    puts = chain_data['puts']
    spot = chain_data['spot_price']
    
    # ============================================
    # PCR (PUT-CALL RATIO) CALCULATION
    # ============================================
    """
    PCR = Total Put OI / Total Call OI
    
    Interpretation:
    - PCR > 1: More puts than calls (bearish sentiment OR hedging)
    - PCR < 1: More calls than puts (bullish sentiment)
    - PCR = 1: Neutral
    
    Note: High PCR can be contrarian bullish (excess fear)
    """
    total_call_oi = sum(c['open_interest'] for c in calls)
    total_put_oi = sum(p['open_interest'] for p in puts)
    pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else 0
    
    total_call_vol = sum(c['volume'] for c in calls)
    total_put_vol = sum(p['volume'] for p in puts)
    pcr_volume = total_put_vol / total_call_vol if total_call_vol > 0 else 0
    
    # ============================================
    # ATM STRADDLE CALCULATION
    # ============================================
    """
    ATM (At-The-Money) = Strike closest to spot price
    Straddle = ATM Call + ATM Put
    
    Use: Measure expected volatility
    Higher straddle = Higher expected move
    """
    atm_strike = min(chain_data['strikes'], key=lambda x: abs(x - spot))
    atm_call = next((c for c in calls if c['strike'] == atm_strike), None)
    atm_put = next((p for p in puts if p['strike'] == atm_strike), None)
    
    atm_straddle_price = 0
    if atm_call and atm_put:
        atm_straddle_price = atm_call['last'] + atm_put['last']
    
    # ============================================
    # MAX PAIN CALCULATION
    # ============================================
    """
    Max Pain = Strike where option writers (sellers) have maximum profit
    
    Theory: Price tends to move toward max pain at expiry
    (controversial but widely watched)
    
    Algorithm:
    For each strike, calculate total value of ITM options
    Max pain = Strike with minimum total ITM value
    """
    max_pain = calculate_max_pain(calls, puts, chain_data['strikes'])
    
    # ============================================
    # BUILD ENRICHED CHAIN
    # ============================================
    enriched_chain = {
        **chain_data,
        'pcr_oi': round(pcr_oi, 4),
        'pcr_volume': round(pcr_volume, 4),
        'atm_strike': atm_strike,
        'atm_straddle_price': round(atm_straddle_price, 2),
        'max_pain_strike': max_pain,
        'total_call_oi': total_call_oi,
        'total_put_oi': total_put_oi,
        'processed_at': datetime.now().isoformat()
    }
    
    # Store and publish
    db.option_chains.insert_one(enriched_chain)
    redis_client.publish('enriched:option_chain', json.dumps(enriched_chain))


def calculate_max_pain(calls, puts, strikes):
    """
    Calculate max pain strike.
    
    For each potential closing price (strike):
    1. Calculate call pain: Sum of (strike - call_strike) * OI for ITM calls
    2. Calculate put pain: Sum of (put_strike - strike) * OI for ITM puts
    3. Total pain = call pain + put pain
    4. Max pain = Strike with minimum total pain
    """
    min_pain = float('inf')
    max_pain_strike = strikes[0]
    
    for closing_price in strikes:
        # Call writers pay if closing > strike
        call_pain = sum(
            c['open_interest'] * max(0, closing_price - c['strike'])
            for c in calls
        )
        
        # Put writers pay if closing < strike  
        put_pain = sum(
            p['open_interest'] * max(0, p['strike'] - closing_price)
            for p in puts
        )
        
        total_pain = call_pain + put_pain
        
        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = closing_price
    
    return max_pain_strike

# ============================================
# SUBSCRIBER - Listens to Redis and dispatches tasks
# ============================================

def subscribe_to_feeds():
    """
    Subscribe to Redis pub/sub and dispatch Celery tasks.
    
    This function runs in main process (not Celery worker).
    It's the bridge between Redis pub/sub and Celery task queue.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe('market:underlying', 'market:option_chain')
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel']
            data = json.loads(message['data'])
            
            # Dispatch to Celery (async)
            if channel == 'market:underlying':
                process_underlying_tick.delay(data)  # .delay() queues task
            elif channel == 'market:option_chain':
                process_option_chain.delay(data)
```

#### Celery Commands

```bash
# ============================================
# STARTING CELERY
# ============================================

# Start worker
celery -A app worker --loglevel=info

# Start worker with specific queue
celery -A app worker -Q high_priority --loglevel=info

# Start worker with concurrency
celery -A app worker --concurrency=4 --loglevel=info

# Start beat scheduler (for periodic tasks)
celery -A app beat --loglevel=info

# ============================================
# MONITORING
# ============================================

# List active tasks
celery -A app inspect active

# List scheduled tasks
celery -A app inspect scheduled

# List registered tasks
celery -A app inspect registered

# Get stats
celery -A app inspect stats

# ============================================
# FLOWER (Web Monitor)
# ============================================

# Install
pip install flower

# Start Flower web interface
celery -A app flower --port=5555

# Access at http://localhost:5555
```

---

### 5.3 Socket Gateway (Flask-SocketIO)

#### What is WebSocket?

WebSocket is a protocol that provides **full-duplex** (bidirectional) communication over a single TCP connection. Unlike HTTP (request-response), WebSocket allows server to push data to clients.

#### HTTP vs WebSocket

```
┌─────────────────────────────────────────────────────────────┐
│              HTTP vs WEBSOCKET                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HTTP (Request-Response):                                   │
│  ─────────────────────────                                  │
│  Client: "Any updates?"  ──────▶  Server                   │
│  Client  ◀──────  "No" :Server                             │
│  Client: "Any updates?"  ──────▶  Server                   │
│  Client  ◀──────  "No" :Server                             │
│  Client: "Any updates?"  ──────▶  Server                   │
│  Client  ◀──────  "Yes! Here's data" :Server               │
│                                                             │
│  Problem: Constant polling wastes resources                 │
│                                                             │
│  WEBSOCKET (Full Duplex):                                   │
│  ─────────────────────────                                  │
│  Client ◀═══════════════════════▶ Server                   │
│         ║ Persistent connection  ║                          │
│         ╠═══════════════════════▶║ (client can send)       │
│         ║◀═══════════════════════╣ (server can push)       │
│                                                             │
│  Benefit: Real-time, efficient, no polling                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Our Socket Gateway Implementation

```python
# services/socket-gateway/app.py

from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import redis
import json
from threading import Thread

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'

# ============================================
# SOCKETIO INITIALIZATION
# ============================================

"""
Key configuration: message_queue=redis_url

This enables horizontal scaling:
- Multiple socket gateway instances can run
- They share messages through Redis
- Client can connect to any instance
"""
socketio = SocketIO(
    app,
    cors_allowed_origins="*",          # Allow all origins (configure in prod)
    message_queue=REDIS_URL,           # Redis for multi-instance support
    async_mode='threading'             # Use threading for background tasks
)

# Track connected clients
connected_clients = {}

# ============================================
# CONNECTION HANDLERS
# ============================================

@socketio.on('connect')
def handle_connect():
    """
    Called when client connects.
    
    request.sid = unique session ID for this connection
    """
    client_id = request.sid
    connected_clients[client_id] = {
        'connected_at': time.time(),
        'rooms': ['general']
    }
    
    # Auto-join general room
    join_room('general')
    
    # Send confirmation to client
    emit('connected', {
        'message': 'Connected to DeltaStream',
        'client_id': client_id,
        'rooms': ['general']
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Called when client disconnects."""
    client_id = request.sid
    if client_id in connected_clients:
        del connected_clients[client_id]

# ============================================
# ROOM-BASED SUBSCRIPTIONS
# ============================================

"""
ROOM CONCEPT:
─────────────
Rooms allow grouping clients for targeted broadcasts.

Room types in our app:
- 'general': All clients (auto-joined)
- 'product:NIFTY': Clients interested in NIFTY underlying
- 'chain:NIFTY': Clients interested in NIFTY option chain

Benefit: Don't send NIFTY data to clients only watching AAPL
"""

@socketio.on('subscribe')
def handle_subscribe(data):
    """
    Handle subscription request.
    
    Client sends: {'type': 'product', 'symbol': 'NIFTY'}
    Result: Client joins room 'product:NIFTY'
    """
    subscription_type = data.get('type')  # 'product' or 'chain'
    symbol = data.get('symbol')           # 'NIFTY', 'AAPL', etc.
    
    if not subscription_type or not symbol:
        emit('error', {'message': 'Invalid subscription'})
        return
    
    # Construct room name
    room = f"{subscription_type}:{symbol}"
    
    # Join room
    join_room(room)
    
    # Track subscription
    client_id = request.sid
    if client_id in connected_clients:
        connected_clients[client_id]['rooms'].append(room)
    
    # Confirm subscription
    emit('subscribed', {
        'room': room,
        'message': f'Subscribed to {room}'
    })
    
    # Send cached data immediately
    send_cached_data(room)

@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Handle unsubscription request."""
    room = f"{data.get('type')}:{data.get('symbol')}"
    leave_room(room)
    emit('unsubscribed', {'room': room})

# ============================================
# BROADCASTING TO ROOMS
# ============================================

def broadcast_to_room(room: str, event: str, data: dict):
    """
    Send message to all clients in a room.
    
    socketio.emit() with room parameter sends to all clients in that room.
    """
    socketio.emit(event, data, room=room)

# ============================================
# REDIS LISTENER (Background Thread)
# ============================================

def redis_listener():
    """
    Listen to Redis pub/sub and broadcast to WebSocket clients.
    
    This is the bridge between:
    - Worker (publishes enriched data to Redis)
    - WebSocket clients (need to receive updates)
    
    Runs in background thread, not blocking main Flask app.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe('enriched:underlying', 'enriched:option_chain')
    
    for message in pubsub.listen():
        if message['type'] != 'message':
            continue
        
        channel = message['channel']
        data = json.loads(message['data'])
        
        if channel == 'enriched:underlying':
            product = data['product']
            
            # Broadcast to general room (all clients)
            socketio.emit('underlying_update', data, room='general')
            
            # Broadcast to product-specific room
            socketio.emit('underlying_update', data, room=f'product:{product}')
        
        elif channel == 'enriched:option_chain':
            product = data['product']
            
            # Broadcast summary to general room
            summary = {
                'product': product,
                'expiry': data['expiry'],
                'spot_price': data['spot_price'],
                'pcr_oi': data['pcr_oi'],
                'atm_straddle_price': data['atm_straddle_price']
            }
            socketio.emit('chain_summary', summary, room='general')
            
            # Broadcast full chain to subscribers
            socketio.emit('chain_update', data, room=f'chain:{product}')

# Start Redis listener in background
listener_thread = Thread(target=redis_listener, daemon=True)
listener_thread.start()

# ============================================
# HTTP ENDPOINTS
# ============================================

@app.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'healthy', 'clients': len(connected_clients)}

@app.route('/metrics')
def metrics():
    """Metrics for monitoring."""
    room_counts = {}
    for client in connected_clients.values():
        for room in client.get('rooms', []):
            room_counts[room] = room_counts.get(room, 0) + 1
    
    return {
        'total_clients': len(connected_clients),
        'rooms': room_counts
    }

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8002)
```

#### WebSocket Client Examples

**JavaScript (Browser):**

```javascript
// examples/subscribe-example.html

// Connect to Socket Gateway
const socket = io('http://localhost:8002');

// Connection events
socket.on('connect', () => {
    console.log('Connected!');
    
    // Subscribe to NIFTY updates
    socket.emit('subscribe', {type: 'product', symbol: 'NIFTY'});
    socket.emit('subscribe', {type: 'chain', symbol: 'NIFTY'});
});

socket.on('disconnect', () => {
    console.log('Disconnected');
});

// Receive underlying price updates
socket.on('underlying_update', (data) => {
    console.log(`${data.product}: ${data.price}`);
    document.getElementById('price').textContent = data.price;
});

// Receive option chain updates
socket.on('chain_summary', (data) => {
    console.log(`PCR: ${data.pcr_oi}, Straddle: ${data.atm_straddle_price}`);
});

// Unsubscribe
function unsubscribe(symbol) {
    socket.emit('unsubscribe', {type: 'product', symbol: symbol});
}
```

**Node.js:**

```javascript
// examples/subscribe-example.js

const io = require('socket.io-client');

const socket = io('http://localhost:8002');

socket.on('connect', () => {
    console.log('Connected to Socket Gateway');
    
    // Subscribe
    socket.emit('subscribe', {type: 'product', symbol: 'NIFTY'});
});

socket.on('underlying_update', (data) => {
    console.log(`[${new Date().toISOString()}] ${data.product}: ${data.price}`);
});

socket.on('chain_summary', (data) => {
    console.log(`\nOption Chain Summary:`);
    console.log(`  Product: ${data.product}`);
    console.log(`  Expiry: ${data.expiry}`);
    console.log(`  Spot: ${data.spot_price}`);
    console.log(`  PCR (OI): ${data.pcr_oi}`);
    console.log(`  ATM Straddle: ${data.atm_straddle_price}`);
});

// Handle Ctrl+C
process.on('SIGINT', () => {
    socket.disconnect();
    process.exit(0);
});
```

---

### 5.4 API Gateway

#### What is an API Gateway?

An API Gateway is a single entry point for all API requests. It handles:
- Request routing
- Authentication
- Rate limiting
- Load balancing
- Request/response transformation

#### Our API Gateway Implementation

```python
# services/api-gateway/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Service URLs (from environment)
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth:8001')
STORAGE_SERVICE_URL = os.getenv('STORAGE_SERVICE_URL', 'http://storage:8003')
ANALYTICS_SERVICE_URL = os.getenv('ANALYTICS_SERVICE_URL', 'http://analytics:8004')

# ============================================
# OPENAPI DOCUMENTATION
# ============================================

@app.route('/api/docs', methods=['GET'])
def api_docs():
    """
    Return OpenAPI specification.
    
    OpenAPI (formerly Swagger) is a standard for describing REST APIs.
    Benefits:
    - Auto-generate documentation
    - Client SDK generation
    - API testing tools (Swagger UI)
    """
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "DeltaStream API",
            "version": "1.0.0"
        },
        "paths": {
            "/api/data/products": {
                "get": {"summary": "Get available products"}
            },
            "/api/data/underlying/{product}": {
                "get": {"summary": "Get underlying ticks"}
            },
            # ... more endpoints
        }
    })

# ============================================
# AUTH ROUTES (Proxy to Auth Service)
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Proxy registration to Auth service.
    
    Gateway pattern: Don't implement logic here, forward to specialized service.
    """
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/register",
            json=request.get_json(),
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Auth service unavailable'}), 503

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Proxy login to Auth service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/login",
            json=request.get_json(),
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Auth service unavailable'}), 503

# ============================================
# DATA ROUTES (Proxy to Storage Service)
# ============================================

@app.route('/api/data/products', methods=['GET'])
def get_products():
    """Get available products."""
    try:
        response = requests.get(
            f"{STORAGE_SERVICE_URL}/products",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Storage service unavailable'}), 503

@app.route('/api/data/underlying/<product>', methods=['GET'])
def get_underlying(product):
    """
    Get underlying ticks.
    
    Query parameters are forwarded to storage service.
    """
    try:
        response = requests.get(
            f"{STORAGE_SERVICE_URL}/underlying/{product}",
            params=request.args.to_dict(),  # Forward query params
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Storage service unavailable'}), 503

@app.route('/api/data/chain/<product>', methods=['GET'])
def get_chain(product):
    """Get option chains."""
    try:
        response = requests.get(
            f"{STORAGE_SERVICE_URL}/option/chain/{product}",
            params=request.args.to_dict(),
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Storage service unavailable'}), 503

# ============================================
# ANALYTICS ROUTES
# ============================================

@app.route('/api/analytics/pcr/<product>', methods=['GET'])
def get_pcr(product):
    """Get PCR analysis."""
    try:
        response = requests.get(
            f"{ANALYTICS_SERVICE_URL}/pcr/{product}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Analytics service unavailable'}), 503

@app.route('/api/analytics/volatility-surface/<product>', methods=['GET'])
def get_volatility_surface(product):
    """Get volatility surface."""
    try:
        response = requests.get(
            f"{ANALYTICS_SERVICE_URL}/volatility-surface/{product}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Analytics service unavailable'}), 503
```

---

### 5.5 Storage Service

The Storage service provides a clean API for database operations. See Section 4.5 (MongoDB) for implementation details.

### 5.6 Auth Service

#### JWT Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  JWT AUTHENTICATION FLOW                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. REGISTRATION                                            │
│  ────────────────                                           │
│  Client ────────▶ POST /register {email, password}          │
│         ◀──────── {token, user}                            │
│                                                             │
│  2. LOGIN                                                   │
│  ─────────                                                  │
│  Client ────────▶ POST /login {email, password}             │
│         ◀──────── {token, user}                            │
│                                                             │
│  3. AUTHENTICATED REQUEST                                   │
│  ───────────────────────────                                │
│  Client ────────▶ GET /api/data                            │
│         ◀──────── (Header: Authorization: Bearer <token>)   │
│                                                             │
│  4. TOKEN STRUCTURE (JWT)                                   │
│  ─────────────────────────                                  │
│  eyJhbGciOiJIUzI1NiJ9.  ← Header (algorithm)               │
│  eyJ1c2VyX2lkIjoiMTIzIn0.  ← Payload (claims)              │
│  SflKxwRJSMeKKF2QT4fwpM  ← Signature (verification)        │
│                                                             │
│  5. TOKEN VERIFICATION                                      │
│  ───────────────────────                                    │
│  Server receives token → Decode → Verify signature          │
│  If valid: Extract user_id, process request                 │
│  If invalid/expired: Return 401 Unauthorized                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

```python
# services/auth/app.py

import jwt
import bcrypt
from datetime import datetime, timedelta

JWT_SECRET = os.getenv('JWT_SECRET', 'change-me-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

@app.route('/register', methods=['POST'])
def register():
    """Register new user."""
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    # Validation
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Check if user exists
    if users_collection.find_one({'email': email}):
        return jsonify({'error': 'User already exists'}), 409
    
    # Hash password (NEVER store plain text!)
    password_hash = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    )
    
    # Create user
    user = {
        'email': email,
        'password_hash': password_hash,
        'created_at': datetime.now()
    }
    result = users_collection.insert_one(user)
    user_id = str(result.inserted_id)
    
    # Generate token
    token = generate_token(user_id, email)
    
    return jsonify({
        'message': 'User registered',
        'token': token,
        'user': {'id': user_id, 'email': email}
    }), 201

@app.route('/login', methods=['POST'])
def login():
    """Login user."""
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    # Find user
    user = users_collection.find_one({'email': email})
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Verify password
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Generate token
    token = generate_token(str(user['_id']), email)
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {'id': str(user['_id']), 'email': email}
    })

def generate_token(user_id: str, email: str) -> str:
    """
    Generate JWT token.
    
    Payload contains:
    - user_id: User identifier
    - email: User email
    - exp: Expiration timestamp
    - iat: Issued at timestamp
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

@app.route('/verify', methods=['POST'])
def verify():
    """Verify JWT token."""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Invalid header'}), 401
    
    token = auth_header[7:]  # Remove 'Bearer '
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return jsonify({
            'valid': True,
            'user_id': payload['user_id'],
            'email': payload['email']
        })
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired', 'valid': False}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token', 'valid': False}), 401
```

### 5.7 Analytics Service

See Section 5.2 (Worker Enricher) for calculation logic. Analytics service exposes HTTP endpoints for:
- PCR trends
- Volatility surface
- Max pain
- OI build-up

### 5.8 Logging Service

```python
# services/logging-service/app.py

"""
Centralized logging service that:
1. Receives structured logs from all services
2. Persists to files
3. Can forward to ELK/Loki
"""

from pathlib import Path

LOG_DIR = '/app/logs'

@app.route('/logs', methods=['POST'])
def ingest_log():
    """Ingest log entry from any service."""
    log_entry = request.get_json()
    
    # Add timestamp if missing
    if 'timestamp' not in log_entry:
        log_entry['timestamp'] = datetime.now().isoformat()
    
    # Write to service-specific file
    service = log_entry.get('service', 'unknown')
    log_file = Path(LOG_DIR) / f"{service}.log"
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    # Publish for real-time monitoring
    redis_client.publish('logs:all', json.dumps(log_entry))
    
    return jsonify({'status': 'logged'}), 201
```

---

## 6. Communication Patterns

### 6.1 Redis Pub/Sub

Already covered in Section 4.4 (Redis). Key pattern:

```python
# Publisher
redis_client.publish('channel_name', json.dumps(data))

# Subscriber
pubsub = redis_client.pubsub()
pubsub.subscribe('channel_name')
for message in pubsub.listen():
    process(message)
```

### 6.2 WebSocket Communication

Already covered in Section 5.3 (Socket Gateway).

### 6.3 REST API

Standard HTTP request-response pattern used by API Gateway.

---

## 7. Caching Strategies

### Cache-Aside Pattern

```python
"""
CACHE-ASIDE PATTERN:
====================

Read:
1. Check cache
2. If hit: return cached data
3. If miss: fetch from DB, store in cache, return

Write:
1. Update database
2. Invalidate/update cache
"""

def get_data(key: str):
    # Step 1: Check cache
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)  # Cache HIT
    
    # Step 2: Cache MISS - fetch from DB
    data = db.collection.find_one({'_id': key})
    
    # Step 3: Store in cache with TTL
    redis_client.setex(key, 300, json.dumps(data))
    
    return data

def update_data(key: str, new_data: dict):
    # Step 1: Update database
    db.collection.update_one({'_id': key}, {'$set': new_data})
    
    # Step 2: Invalidate cache (next read will refresh)
    redis_client.delete(key)
    
    # OR: Update cache immediately
    redis_client.setex(key, 300, json.dumps(new_data))
```

### TTL (Time-To-Live) Strategy

```python
# Different TTLs for different data types
CACHE_TTLS = {
    'latest_price': 60,        # 1 minute - frequently updated
    'option_chain': 300,       # 5 minutes - updates every few minutes
    'user_session': 3600,      # 1 hour - longer lived
    'static_config': 86400,    # 1 day - rarely changes
}

def cache_with_ttl(key: str, data: dict, data_type: str):
    ttl = CACHE_TTLS.get(data_type, 300)
    redis_client.setex(key, ttl, json.dumps(data))
```

---

## 8. Message Queuing with Celery

Already covered in Section 5.2 (Worker Enricher).

---

## 9. Observability & Monitoring

### Structured Logging

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Usage
logger.info(
    "order_processed",
    order_id="12345",
    amount=100.50,
    status="completed"
)

# Output (JSON):
# {"timestamp": "2025-01-15T10:30:00Z", "event": "order_processed", 
#  "order_id": "12345", "amount": 100.50, "status": "completed"}
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['endpoint']
)

# Record metrics
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    latency = time.time() - request.start_time
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(endpoint=request.path).observe(latency)
    return response

# Expose metrics endpoint
@app.route('/metrics')
def metrics():
    return generate_latest()
```

---

## 10. CI/CD Pipeline

See `.github/workflows/ci.yml` for full implementation.

```yaml
# Simplified CI/CD stages
jobs:
  lint:      # Check code style
  test:      # Run unit tests
  build:     # Build Docker images
  deploy:    # Deploy to Kubernetes
```

---

## 11. Security Best Practices

```
┌─────────────────────────────────────────────────────────────┐
│                  SECURITY CHECKLIST                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✓ Never store passwords in plain text (use bcrypt)        │
│  ✓ Use environment variables for secrets                   │
│  ✓ Validate all user input                                 │
│  ✓ Use HTTPS in production                                 │
│  ✓ Set proper CORS policies                                │
│  ✓ Implement rate limiting                                 │
│  ✓ Use JWT with short expiration                           │
│  ✓ Rotate secrets regularly                                │
│  ✓ Use Kubernetes Secrets (not ConfigMaps) for sensitive   │
│  ✓ Enable TLS for Redis and MongoDB                        │
│  ✓ Run containers as non-root user                         │
│  ✓ Scan images for vulnerabilities                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Scaling Strategies

### Horizontal Scaling

```bash
# Docker Compose
docker-compose up -d --scale worker-enricher=5

# Kubernetes
kubectl scale deployment worker-enricher --replicas=5
```

### Auto-scaling with HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
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

---

## 13. Interview Questions & Answers

### Docker & Containerization

**Q1: What is the difference between a Docker image and a container?**
```
Answer:
- Image: Read-only template with instructions for creating a container.
         Like a class in OOP. Created from Dockerfile.
- Container: Running instance of an image. Like an object in OOP.
             Has writable layer, can be started/stopped/deleted.
```

**Q2: What is Docker layer caching and why is it important?**
```
Answer:
Docker builds images in layers. Each instruction creates a layer.
If a layer hasn't changed, Docker reuses cached layer.

Best practice: Put things that change rarely (dependencies) before 
things that change often (code).

# Good Dockerfile
COPY requirements.txt .    # Changes rarely
RUN pip install -r requirements.txt
COPY . .                   # Changes often
```

**Q3: How would you reduce Docker image size?**
```
Answer:
1. Use slim/alpine base images (python:3.11-slim vs python:3.11)
2. Multi-stage builds (build in one stage, copy only needed files)
3. Combine RUN commands to reduce layers
4. Remove unnecessary files (.git, __pycache__, docs)
5. Use .dockerignore file
```

### Kubernetes

**Q4: Explain the difference between a Pod, Deployment, and Service.**
```
Answer:
- Pod: Smallest deployable unit. Contains 1+ containers sharing network/storage.
       Ephemeral - can be terminated anytime.

- Deployment: Manages Pods. Ensures desired number of replicas.
              Handles rolling updates and rollbacks.

- Service: Stable network endpoint for Pods. Load balances across Pods.
           Types: ClusterIP (internal), NodePort, LoadBalancer (external)
```

**Q5: What is a Kubernetes Ingress?**
```
Answer:
Ingress manages external access to services, typically HTTP.
Provides:
- URL routing (api.example.com -> api-service)
- SSL termination
- Load balancing
- Name-based virtual hosting

Requires an Ingress Controller (nginx, traefik, etc.)
```

**Q6: How does Kubernetes achieve self-healing?**
```
Answer:
1. Liveness Probe: If fails, container is restarted
2. Readiness Probe: If fails, Pod removed from Service endpoints
3. ReplicaSet: Maintains desired number of Pods
4. Deployment: Recreates failed Pods automatically

Example:
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
```

### Redis

**Q7: Explain Redis Pub/Sub vs Redis Streams.**
```
Answer:
Pub/Sub:
- Fire-and-forget messaging
- Messages lost if no subscriber
- No persistence
- Use case: Real-time notifications

Streams:
- Persistent log-like data structure
- Consumer groups with acknowledgment
- Messages persist until deleted
- Use case: Event sourcing, reliable messaging

In our project, we use Pub/Sub for real-time broadcasts where 
occasional message loss is acceptable.
```

**Q8: What caching strategies do you know?**
```
Answer:
1. Cache-Aside (Lazy Loading):
   - Check cache → If miss, fetch from DB → Store in cache
   - Pros: Only requested data cached
   - Cons: Cache miss = slow first request

2. Write-Through:
   - Write to cache and DB simultaneously
   - Pros: Cache always consistent
   - Cons: Write latency, cache may have unused data

3. Write-Behind (Write-Back):
   - Write to cache, async write to DB
   - Pros: Fast writes
   - Cons: Risk of data loss

4. Refresh-Ahead:
   - Proactively refresh before expiry
   - Pros: Always fresh data
   - Cons: May refresh unused data
```

### Celery & Message Queues

**Q9: What is the difference between Celery broker and backend?**
```
Answer:
Broker: Transports messages from producer to worker
        Stores task queue (Redis, RabbitMQ)
        
Backend: Stores task results and status
         Optional - only needed if you check results
         (Redis, database)

Example:
celery_app = Celery(
    broker='redis://localhost:6379/1',   # Task queue
    backend='redis://localhost:6379/2'   # Results
)
```

**Q10: How do you handle failed Celery tasks?**
```
Answer:
1. Automatic Retries:
   @celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})

2. Exponential Backoff:
   @celery_app.task(retry_backoff=True)

3. Dead Letter Queue:
   On final failure, push to DLQ for manual inspection

4. Idempotency:
   Check if task was already processed before executing

5. Monitoring:
   Use Flower to monitor task status and failures
```

### WebSocket

**Q11: How does WebSocket differ from HTTP polling?**
```
Answer:
HTTP Polling:
Client → "Any updates?" → Server
Client ← "No" ← Server
(Repeat every N seconds)
Wastes bandwidth, high latency

WebSocket:
Client ← → Server (persistent connection)
Server can push immediately
Lower latency, efficient

Use WebSocket for: Real-time apps (chat, trading, gaming)
Use HTTP for: Standard CRUD operations, REST APIs
```

**Q12: How do you scale WebSocket servers horizontally?**
```
Answer:
Challenge: WebSocket connections are stateful

Solution: Use message broker (Redis) to sync messages across instances

# Flask-SocketIO with Redis
socketio = SocketIO(app, message_queue='redis://localhost:6379')

When server A needs to send to client on server B:
1. Server A publishes to Redis
2. All servers receive message
3. Server B (with client) delivers message
```

### MongoDB

**Q13: When would you choose MongoDB over PostgreSQL?**
```
Answer:
Choose MongoDB when:
- Flexible/evolving schema
- JSON-like documents fit your data
- Horizontal scaling needed (sharding)
- Rapid prototyping
- Semi-structured data

Choose PostgreSQL when:
- Complex transactions (ACID)
- Complex joins needed
- Strict data integrity
- Relational data model
- Advanced SQL features needed
```

**Q14: What is MongoDB aggregation pipeline?**
```
Answer:
Aggregation pipeline processes documents through stages:

db.orders.aggregate([
  { $match: { status: "completed" } },   # Filter
  { $group: { _id: "$product", total: { $sum: "$amount" } } },  # Group
  { $sort: { total: -1 } },              # Sort
  { $limit: 10 }                         # Limit
])

Stages: $match, $group, $sort, $project, $lookup (join), $unwind, etc.
```

### System Design

**Q15: Design a real-time stock price notification system.**
```
Answer:
Components:
1. Data Ingestion: Receive price updates from exchange
2. Message Broker: Kafka/Redis for distributing updates
3. Processing: Calculate alerts (price > threshold)
4. Notification Service: Send alerts via WebSocket/push
5. Storage: Store historical prices in time-series DB

Flow:
Exchange → Kafka → Alert Worker → Redis Pub/Sub → WebSocket → Client

Scaling:
- Kafka: Partition by symbol
- Workers: Scale horizontally
- WebSocket: Redis adapter for multi-instance
```

**Q16: How would you design a rate limiter?**
```
Answer:
Algorithms:
1. Token Bucket: Tokens added at fixed rate, request uses token
2. Sliding Window: Count requests in past N seconds
3. Fixed Window: Reset count each minute/hour

Implementation with Redis:
def is_rate_limited(user_id, limit=100, window=60):
    key = f"rate_limit:{user_id}"
    current = redis.incr(key)
    if current == 1:
        redis.expire(key, window)
    return current > limit
```

---

## 14. Hands-On Exercises

### Exercise 1: Add a New Product
```
Task: Add "RELIANCE" to the feed generator and verify data flows through the system.

Steps:
1. Edit services/feed-generator/app.py
2. Add to PRODUCTS list and BASE_PRICES dict
3. Restart feed-generator: docker-compose restart feed-generator
4. Verify: curl http://localhost:8000/api/data/products
5. Subscribe via WebSocket and confirm updates
```

### Exercise 2: Add Rate Limiting to API Gateway
```
Task: Implement rate limiting (100 requests/minute per IP)

Steps:
1. Install flask-limiter: pip install Flask-Limiter
2. Add to api-gateway:
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=get_remote_address)
   
   @app.route('/api/data/products')
   @limiter.limit("100/minute")
   def get_products():
       ...
3. Test: Send >100 requests and verify 429 response
```

### Exercise 3: Add Prometheus Metrics
```
Task: Add custom metrics to track option chain processing time

Steps:
1. Install prometheus_client
2. Add histogram metric for processing time
3. Expose /metrics endpoint
4. Configure Prometheus to scrape
5. Create Grafana dashboard
```

---

## 15. Troubleshooting Guide

### Common Issues

**Issue: Services not starting**
```bash
# Check logs
docker-compose logs <service-name>

# Common causes:
# - Port already in use
# - Missing environment variables
# - Dependency service not ready
```

**Issue: No data flowing**
```bash
# Check Redis pub/sub
docker-compose exec redis redis-cli
> SUBSCRIBE market:underlying

# Check MongoDB
docker-compose exec mongodb mongosh option_aro
> db.underlying_ticks.countDocuments()

# Restart worker
docker-compose restart worker-enricher
```

**Issue: WebSocket not connecting**
```bash
# Check socket gateway logs
docker-compose logs socket-gateway

# Verify health
curl http://localhost:8002/health

# Check CORS settings if browser client
```

**Issue: High memory usage**
```bash
# Check container stats
docker stats

# Solutions:
# - Reduce worker concurrency
# - Add memory limits in docker-compose
# - Check for memory leaks
```

---

## Conclusion

This tutorial covered the complete DeltaStream architecture:

1. **Infrastructure**: Docker, Kubernetes, Redis, MongoDB
2. **Microservices**: Feed Generator, Worker, Socket Gateway, API Gateway, etc.
3. **Patterns**: Pub/Sub, WebSockets, Caching, Message Queuing
4. **DevOps**: CI/CD, Monitoring, Logging
5. **Interview Prep**: 16 common questions with detailed answers

**Next Steps:**
1. Run the project locally: `docker-compose up -d`
2. Explore each service's code
3. Try the hands-on exercises
4. Build your own features
5. Deploy to Kubernetes

**Happy Learning! 🚀**
