### **2. EVENT-DRIVEN ARCHITECTURE**

**What it is:**
Services communicate by publishing and subscribing to events rather than direct API calls. When something happens, an event is published, and interested services react to it.

**In your project:**
```python
# Feed Generator publishes events
redis_client.publish('market:underlying', json.dumps(tick_data))
redis_client.publish('market:option_chain', json.dumps(chain_data))

# Worker Enricher subscribes to events
pubsub.subscribe('market:underlying', 'market:option_quote', 'market:option_chain')
```

**Benefits:**
- **Loose Coupling**: Services don't need to know about each other
- **Asynchronous**: Publisher doesn't wait for subscribers
- **Multiple Consumers**: Many services can react to same event
- **Resilience**: If a subscriber is down, events aren't lost (Redis handles buffering)

**5 Channels in your project:**
1. `market:underlying` - Raw underlying price ticks
2. `market:option_quote` - Individual option quotes
3. `market:option_chain` - Complete option chains
4. `enriched:underlying` - Processed underlying data
5. `enriched:option_chain` - Enriched chain with analytics

---
