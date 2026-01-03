# DeltaStream Examples

> **Ready-to-run code samples for testing and integrating with DeltaStream APIs**

## 🎯 Quick Start

```bash
# 1. Start DeltaStream
cd .. && make up

# 2. Test REST APIs
cd examples
./curl-examples.sh

# 3. Test WebSocket (Node.js)
npm install
node subscribe-example.js

# 4. Test WebSocket (Browser)
open subscribe-example.html
```

---

## 📦 What's Included

### REST API Testing

#### 1. **curl-examples.sh**
Shell script to test all REST endpoints

**What it does:**
- Health check
- Get products list
- Get underlying prices (NIFTY)
- Get option chains
- Get analytics (PCR, volatility surface)
- User registration

**Usage:**
```bash
chmod +x curl-examples.sh
./curl-examples.sh
```

**Requirements:** curl, jq (for JSON formatting)

---

#### 2. **postman-collection.json**
Pre-configured Postman collection with all API endpoints

**What it includes:**
- Authentication (register, login, verify, refresh)
- Market data (products, underlying, chains, expiries)
- Analytics (PCR trends, volatility surface)
- AI Analyst (market pulse, sentiment, chatbot)

**Usage:**
1. Open Postman
2. Import → File → Select `postman-collection.json`
3. Set environment variable: `BASE_URL = http://localhost:8000`
4. Click any request → Send

---

### WebSocket Clients

#### 3. **subscribe-example.js**
Node.js WebSocket client for real-time data streaming

**What it does:**
- Connects to Socket Gateway (port 8002)
- Subscribes to NIFTY updates
- Receives real-time price & chain updates
- Handles reconnection gracefully

**Usage:**
```bash
npm install  # Install socket.io-client
node subscribe-example.js

# With custom product
PRODUCT=BANKNIFTY node subscribe-example.js
```

**Output:**
```
Connected to Socket Gateway
Client ID: abc123
[2025-01-03T10:30:00] NIFTY Price: 21543.25

[Chain Summary] NIFTY (2025-01-25)
  Spot: 21543.25
  PCR (OI): 1.15
  Max Pain: 21500
```

---

#### 4. **subscribe-example.html**
Browser-based WebSocket demo with visual UI

**What it does:**
- Connect/disconnect WebSocket from browser
- Subscribe to multiple products
- Display live updates in webpage
- Show connection status

**Usage:**
```bash
# Simply open in browser
open subscribe-example.html
# or
firefox subscribe-example.html
```

**Features:**
- Real-time price updates
- Connection status indicator
- Multi-product subscription
- Pure HTML/JS (no build step)

---

### Dependencies

#### 5. **package.json**
Node.js dependencies for JavaScript examples

**Contains:**
```json
{
  "dependencies": {
    "socket.io-client": "^4.5.0"
  }
}
```

**Install:**
```bash
npm install
```

---

## 🔧 Customization

### Change Product
```bash
# In curl-examples.sh
PRODUCT="BANKNIFTY"  # Change this

# In subscribe-example.js
PRODUCT=BANKNIFTY node subscribe-example.js

# In subscribe-example.html
Edit line: symbol: 'BANKNIFTY'
```

### Change Server URL
```bash
# In curl-examples.sh
BASE_URL="https://api.deltastream.com"

# In subscribe-example.js
SOCKET_URL=https://ws.deltastream.com node subscribe-example.js

# In subscribe-example.html
Edit: const socket = io('https://ws.deltastream.com')
```

---

## 📚 Use Cases

### For Developers
- **Quick testing**: Verify API responses
- **Integration templates**: Copy code for your app
- **Debugging**: Test specific endpoints in isolation

### For QA Engineers
- **Manual testing**: Use Postman collection
- **Automation**: Adapt curl-examples.sh for CI/CD

### For Frontend Developers
- **WebSocket reference**: See how to connect and subscribe
- **Event handling**: Learn event names and data structures

---

## 🎓 Learning Path

1. **Start with curl**: Understand REST APIs
2. **Try Postman**: Interactive API exploration
3. **Test WebSocket (Browser)**: See real-time updates visually
4. **Study JS client**: Learn programmatic WebSocket usage
5. **Build your own**: Adapt examples for your needs

---

## 💡 Tips

- **Always start DeltaStream first**: `make up` from project root
- **Check logs if errors**: `make logs` to see service output
- **Use jq for formatting**: Install with `brew install jq` (Mac)
- **WebSocket requires Socket Gateway**: Ensure port 8002 is accessible

---

## 📖 Related Documentation

- **API Reference**: [../docs/api-reference/](../docs/api-reference/) - Detailed endpoint docs
- **Tutorial**: [../docs/tutorials/](../docs/tutorials/) - Build from scratch
- **Quickstart**: [../docs/tutorials/quickstart.md](../docs/tutorials/quickstart.md) - 10-minute setup

---

**Ready to test?** Start with `./curl-examples.sh` 🚀
