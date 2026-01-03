# Architecture Documentation

> **System design and architectural decisions for DeltaStream**

## 📚 Contents

### [System Design](system-design.md)
High-level overview of the DeltaStream architecture
- Service interactions
- Data flow diagrams
- Deployment architecture

### [Microservices Architecture](microservices.md)
Deep dive into microservices patterns used
- Service decomposition
- Communication patterns
- Service discovery

### [Data Flow](data-flow.md)
Complete data flow through the system
- From feed generation to client display
- Event-driven architecture
- Pub/sub messaging

### [Tech Stack](tech-stack.md)
Technologies and frameworks used
- Backend: Python, Flask, Celery
- Data: MongoDB, Redis
- Infrastructure: Docker, Kubernetes
- AI/ML: LangChain, HuggingFace

---

## 🎯 Quick Reference

- **Data Layer**: MongoDB (persistence), Redis (cache/pub-sub)
- **Processing**: Celery workers for async tasks
- **API Layer**: Flask REST + Flask-SocketIO
- **Deployment**: Docker Compose (dev), Kubernetes (prod)

---

*These architecture docs provide the blueprint for understanding how DeltaStream is designed and why specific architectural decisions were made.*
