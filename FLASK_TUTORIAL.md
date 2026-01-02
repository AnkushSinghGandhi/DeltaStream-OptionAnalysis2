# Implement DeltaStream Backend with Flask

This tutorial guides you through creating the DeltaStream Backend using **Flask** instead of FastAPI. This implementation mirrors the logic of the original project.

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Project Setup

1. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Flask and Flask-CORS**:
   ```bash
   pip install flask flask-cors
   ```

3. **Create `app.py`**:
   This file will contain the entire backend logic.

---

## Code Implementation (`app.py`)

Copy the following code into your `app.py`. This code includes all necessary logic:
- Mock Data Generation (Prices, Expiries)
- Black-Scholes Option Pricing Model
- API Endpoints simulating the original backend

```python
import math
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

# --- Configuration ---
app = Flask(__name__)
CORS(app)  # Allow frontend to access API

# Constants
PRODUCTS = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'AAPL', 'TSLA', 'SPY', 'QQQ']
BASE_PRICES = {
    'NIFTY': 24500, 'BANKNIFTY': 52000, 'FINNIFTY': 23500, 'SENSEX': 80500,
    'AAPL': 195, 'TSLA': 248, 'SPY': 592, 'QQQ': 510,
}
STRIKE_INTERVALS = {
    'NIFTY': 50, 'BANKNIFTY': 100, 'FINNIFTY': 25, 'SENSEX': 100,
    'AAPL': 2.5, 'TSLA': 5, 'SPY': 1, 'QQQ': 1,
}

# State
price_store = {p: BASE_PRICES.get(p, 100) for p in PRODUCTS}

# --- Helper Functions ---

def norm_cdf(x):
    """Standard normal cumulative distribution function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def black_scholes_call(S, K, T, r, sigma):
    """Calculate Call Option Price."""
    if T <= 0 or sigma <= 0: return max(0, S - K)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

def black_scholes_put(S, K, T, r, sigma):
    """Calculate Put Option Price."""
    if T <= 0 or sigma <= 0: return max(0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def generate_expiries():
    """Generate next 4 weekly Thursday expiries."""
    today = datetime.now()
    expiries = []
    for i in range(1, 5):
        days_ahead = (3 - today.weekday()) % 7 
        if days_ahead == 0 and i == 1: days_ahead = 7
        thursday = today + timedelta(days=days_ahead + 7*(i-1))
        expiries.append(thursday.strftime('%Y-%m-%d'))
    return sorted(list(set(expiries)))

def update_prices():
    """Simulate random price movement."""
    for p in PRODUCTS:
        base = BASE_PRICES[p]
        change = price_store[p] * random.uniform(-0.001, 0.001)
        price_store[p] = max(base * 0.9, min(base * 1.1, price_store[p] + change))

def generate_chain(product):
    """Generate option chain data."""
    spot = price_store[product]
    interval = STRIKE_INTERVALS.get(product, 50)
    atm = round(spot / interval) * interval
    strikes = [atm + (i - 10) * interval for i in range(21)]
    expiry = generate_expiries()[0]
    
    # Calculate Time to expiry in years
    days = max(1, (datetime.strptime(expiry, '%Y-%m-%d') - datetime.now()).days)
    T = days / 365.0
    r = 0.06 # Risk-free rate

    calls = []
    puts = []

    for strike in strikes:
        moneyness = (strike - spot) / spot
        iv = 0.15 + abs(moneyness) * 0.5  # IV Smile
        
        # Call
        c_iv = iv + random.uniform(-0.01, 0.01)
        c_price = black_scholes_call(spot, strike, T, r, c_iv)
        c_oi = int(random.uniform(10000, 50000) * math.exp(-abs(moneyness)*3))
        
        calls.append({
            'strike': strike, 'last': round(c_price, 2), 'iv': round(c_iv, 4),
            'open_interest': c_oi, 'volume': int(c_oi * 0.3),
            'oi_change': int(random.uniform(-1000, 1000))
        })

        # Put
        p_iv = iv + random.uniform(-0.01, 0.01)
        p_price = black_scholes_put(spot, strike, T, r, p_iv)
        p_oi = int(random.uniform(10000, 50000) * math.exp(-abs(moneyness)*3))
        
        puts.append({
            'strike': strike, 'last': round(p_price, 2), 'iv': round(p_iv, 4),
            'open_interest': p_oi, 'volume': int(p_oi * 0.3),
            'oi_change': int(random.uniform(-1000, 1000))
        })

    return {
        'product': product, 'expiry': expiry, 'spot_price': round(spot, 2),
        'calls': calls, 'puts': puts, 'strikes': strikes,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

# --- Routes ---

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "service": "deltastream-flask"})

@app.route('/api/data/products')
def get_products():
    return jsonify({"products": PRODUCTS})

@app.route('/api/data/chain/<product>')
def get_chain_endpoint(product):
    if product not in PRODUCTS: return jsonify({"error": "Not Found"}), 404
    update_prices()
    return jsonify({'product': product, 'chains': [generate_chain(product)]})

@app.route('/api/data/underlying/<product>')
def get_underlying(product):
    if product not in PRODUCTS: return jsonify({"error": "Not Found"}), 404
    update_prices()
    limit = int(request.args.get('limit', 100))
    current = price_store[product]
    ticks = []
    for i in range(limit):
        ticks.append({
            'price': round(current * (1 + random.uniform(-0.0005, 0.0005)), 2),
            'timestamp': (datetime.utcnow() - timedelta(seconds=i)).isoformat() + 'Z'
        })
    return jsonify({'product': product, 'ticks': list(reversed(ticks))})

if __name__ == '__main__':
    print("Starting Flask Server on port 8001...")
    # Port 8001 matches the original project
    app.run(host='0.0.0.0', port=8001, debug=True)
```

## Running the Server

1. Save the file.
2. Run: `python app.py`
3. The API will be available at `http://localhost:8001`.

## Next Steps

This backend provides the same data structure as the original `server.py`. You can now:
- Connect a frontend to `http://localhost:8001`.
- Expand the logic by adding more analytics endpoints (like PCR, Max Pain) following the same pattern.
