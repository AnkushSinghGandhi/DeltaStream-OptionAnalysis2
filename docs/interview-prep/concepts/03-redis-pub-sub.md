### **3. REDIS PUB/SUB**

**What it is:**
Redis Publish/Subscribe is a messaging pattern where publishers send messages to channels without knowing who will receive them, and subscribers listen to channels of interest.

**How it works:**
```
Publisher → Redis Channel → Multiple Subscribers
(Fire and forget)      (Message broker)     (All receive message)
```

**In your code:**
```python
# Publisher (Feed Generator)
redis_client.publish('market:underlying', json.dumps({
    'product': 'NIFTY',
    'price': 21543.25,
    'timestamp': '2025-01-15T10:30:00Z'
}))

# Subscriber (Worker Enricher)
pubsub = redis_client.pubsub()
pubsub.subscribe('market:underlying')
for message in pubsub.listen():
    if message['type'] == 'message':
        data = json.loads(message['data'])
        process_underlying_tick.delay(data)  # Dispatch to Celery
```

**Key Differences from Queue:**
- **Pub/Sub**: Message delivered to ALL subscribers (1-to-many)
- **Queue**: Message delivered to ONE consumer (1-to-1)

---
