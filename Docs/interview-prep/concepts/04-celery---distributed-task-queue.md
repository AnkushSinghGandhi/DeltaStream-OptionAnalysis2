### **4. CELERY - DISTRIBUTED TASK QUEUE**

**What it is:**
Celery is a distributed task queue system that allows you to run functions asynchronously in background workers.

**Architecture:**
```
Producer → Broker (Redis) → Worker → Result Backend (Redis)
(Your app)  (Queue)        (Celery)   (Stores results)
```

**In your code:**
```python
# Define task
@celery_app.task
def process_option_chain(chain_data):
    # Heavy computation here
    calculate_pcr()
    calculate_max_pain()
    store_in_mongodb()

# Dispatch task (non-blocking)
process_option_chain.delay(chain_data)  # Returns immediately
```

**Why use Celery:**
- Offload heavy computations from API requests
- Retry failed tasks automatically
- Scale workers independently
- Handle long-running tasks without blocking

**Your Celery configuration:**
```python
celery_app.conf.update(
    task_serializer='json',
    task_acks_late=True,              # Critical for reliability
    worker_prefetch_multiplier=1,     # One task at a time per worker
    task_reject_on_worker_lost=True,  # Re-queue if worker crashes
)
```

---
