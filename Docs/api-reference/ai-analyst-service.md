# AI Analyst Service API

> **LLM-powered market insights**

**Base URL**: `http://localhost:8000/api/ai`  
**Port**: 8006

## Endpoints

### GET /ai/pulse?product=NIFTY
Market summary with LLM

**Response**:
```json
{
  "product": "NIFTY",
  "analysis": "Neutral sentiment. PCR of 1.15 indicates balanced market...",
  "data": {
    "pcr": 1.15,
    "pcr_vol": 0.98
  }
}
```

### GET /ai/sentiment
News sentiment analysis

**Response**:
```json
{
  "sentiment": "Bullish",
  "headlines": [
    "Nifty hits all-time high...",
    "Banking stocks surge..."
  ]
}
```

### POST /ai/chat
RAG chatbot Q&A

**Request**:
```json
{
  "query": "What is Max Pain?"
}
```

**Response**:
```json
{
  "answer": "Based on documentation, Max Pain is..."
}
```

## Related
- [Tutorial Chapter 9](../tutorials/complete-guide/chapter09.md)
