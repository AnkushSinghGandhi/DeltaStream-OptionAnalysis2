# API Reference

> **Complete REST API documentation for DeltaStream**

## 🚀 Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.deltastream.com` (example)

All APIs are accessed through the API Gateway.

---

## 📚 Quick Links

- [Authentication API](auth-service.md) - Login, register, token management
- [Storage API](storage-service.md) - Market data retrieval
- [WebSocket API](websocket-api.md) - Real-time streaming
- [Analytics API](analytics-service.md) - Advanced calculations
- [AI Analyst API](ai-analyst-service.md) - LLM-powered insights

---

## 🔑 Authentication

All protected endpoints require a JWT token in the `Authorization` header:

```http
Authorization: Bearer <your_jwt_token>
```

### Get a Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

**Response:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "email": "user@example.com",
    "id": "507f1f77bcf86cd799439011"
  }
}
```

---

## 📊 Response Format

### Success Response
```json
{
  "data": { ... },
  "status": "success"
}
```

### Error Response
```json
{
  "error": "Error message",
  "status": "error",
  "code": 400
}
```

---

## 🌐 API Endpoints Summary

### Authentication (`/api/auth/*`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Create new user | No |
| POST | `/auth/login` | Login & get token | No |
| POST | `/auth/verify` | Verify token | Yes |
| POST | `/auth/refresh` | Refresh token | Yes |

### Market Data (`/api/data/*`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/data/products` | List available products | No |
| GET | `/data/expiries/:product` | Get expiry dates | No |
| GET | `/data/underlying/:product` | Latest underlying price | No |
| GET | `/data/underlying/:product/history` | Historical prices | No |
| GET | `/data/options/:symbol` | Option quote | No |
| GET | `/data/chain/:product/:expiry` | Complete option chain | No |

### Analytics (`/api/analytics/*`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/analytics/pcr_trends/:product` | PCR over time | No |
| GET | `/analytics/volatility_surface/:product` | IV surface | No |

### AI Analyst (`/api/ai/*`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/ai/market_pulse/:product` | LLM market summary | No |
| GET | `/ai/sentiment/:product` | News sentiment | No |
| POST | `/ai/ask` | RAG chatbot Q&A | No |

### System (`/api/*`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/health` | System health | No |
| GET | `/docs` | OpenAPI spec | No |

---

## 💡 Common Use Cases

### 1. Get Current Market State
```bash
# Get latest NIFTY price
curl http://localhost:8000/api/data/underlying/NIFTY

# Get option chain
curl http://localhost:8000/api/data/chain/NIFTY/2025-01-25

# Get analytics
curl http://localhost:8000/api/analytics/pcr_trends/NIFTY
```

### 2. Historical Analysis
```bash
# Get price history (last 7 days)
curl "http://localhost:8000/api/data/underlying/NIFTY/history?days=7"
```

### 3. AI Insights
```bash
# Get market pulse
curl http://localhost:8000/api/ai/market_pulse/NIFTY

# Ask a question
curl -X POST http://localhost:8000/api/ai/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How is PCR calculated?"}'
```

---

## 🔌 WebSocket Connection

```javascript
const socket = io('http://localhost:8002');

// Subscribe to NIFTY updates
socket.emit('subscribe', {type: 'product', symbol: 'NIFTY'});

// Receive real-time updates
socket.on('underlying_update', (data) => {
  console.log('Price:', data.price);
});
```

See [WebSocket API](websocket-api.md) for full documentation.

---

## ⚡ Rate Limiting

- **Default**: 100 requests/minute per IP
- **Authenticated**: 1000 requests/minute per user
- **WebSocket**: No rate limiting (connection-based)

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1641033600
```

---

## 🧪 Testing APIs

### Using cURL
See [examples/curl-examples.sh](../../examples/curl-examples.sh)

### Using Postman
Import [examples/postman-collection.json](../../examples/postman-collection.json)

### Using Python
```python
import requests

response = requests.get('http://localhost:8000/api/data/products')
products = response.json()['data']
print(products)
```

---

## 📚 Detailed Documentation

Click through to service-specific docs for full endpoint details, request/response schemas, and examples.
