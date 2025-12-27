#!/usr/bin/env python3
"""
DeltaStream Dashboard Backend

Provides:
1. REST API endpoints for option chain data and analytics
2. WebSocket support for real-time streaming
3. Mock data generation for demonstration
"""

import os
import json
import random
import math
from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
import asyncio

# Configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/deltastream')

# Mock data products
PRODUCTS = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'AAPL', 'TSLA', 'SPY', 'QQQ']

# Base prices for products
BASE_PRICES = {
    'NIFTY': 24500,
    'BANKNIFTY': 52000,
    'FINNIFTY': 23500,
    'SENSEX': 80500,
    'AAPL': 195,
    'TSLA': 248,
    'SPY': 592,
    'QQQ': 510,
}

# Strike intervals
STRIKE_INTERVALS = {
    'NIFTY': 50,
    'BANKNIFTY': 100,
    'FINNIFTY': 25,
    'SENSEX': 100,
    'AAPL': 2.5,
    'TSLA': 5,
    'SPY': 1,
    'QQQ': 1,
}

# Store for simulated prices
price_store = {}
chain_store = {}

def generate_expiries():
    """Generate realistic expiry dates."""
    today = datetime.now()
    expiries = []
    
    # Weekly expiries (next 4 weeks)
    for i in range(1, 5):
        thursday = today + timedelta(days=(3 - today.weekday()) % 7 + 7 * (i - 1))
        expiries.append(thursday.strftime('%Y-%m-%d'))
    
    # Monthly expiries (next 3 months)
    for i in range(1, 4):
        month = (today.month + i - 1) % 12 + 1
        year = today.year + ((today.month + i - 1) // 12)
        last_day = datetime(year, month, 28)
        while last_day.weekday() != 3:  # Thursday
            last_day -= timedelta(days=1)
        expiries.append(last_day.strftime('%Y-%m-%d'))
    
    return sorted(list(set(expiries)))

def generate_option_chain(product: str, spot_price: float = None):
    """Generate realistic option chain data."""
    if spot_price is None:
        spot_price = BASE_PRICES.get(product, 100) * (1 + random.uniform(-0.02, 0.02))
    
    interval = STRIKE_INTERVALS.get(product, 50)
    atm_strike = round(spot_price / interval) * interval
    
    # Generate 21 strikes (10 below, ATM, 10 above)
    strikes = [atm_strike + (i - 10) * interval for i in range(21)]
    
    expiry = generate_expiries()[0]  # Use nearest expiry
    days_to_expiry = max(1, (datetime.strptime(expiry, '%Y-%m-%d') - datetime.now()).days)
    
    calls = []
    puts = []
    
    for strike in strikes:
        # Calculate base IV using ATM volatility with smile
        moneyness = (strike - spot_price) / spot_price
        base_iv = 0.15 + abs(moneyness) * 0.5  # IV smile
        
        # Call option
        call_iv = base_iv + random.uniform(-0.02, 0.02)
        call_price = max(0.05, black_scholes_call(spot_price, strike, days_to_expiry/365, 0.06, call_iv))
        call_oi = int(random.uniform(10000, 500000) * math.exp(-abs(moneyness) * 3))
        call_volume = int(call_oi * random.uniform(0.1, 0.5))
        
        calls.append({
            'strike': strike,
            'last': round(call_price, 2),
            'bid': round(call_price * 0.98, 2),
            'ask': round(call_price * 1.02, 2),
            'iv': round(call_iv, 4),
            'delta': round(calculate_delta(spot_price, strike, days_to_expiry/365, 0.06, call_iv, 'call'), 4),
            'gamma': round(random.uniform(0.001, 0.01), 4),
            'theta': round(-random.uniform(0.5, 5), 2),
            'vega': round(random.uniform(5, 20), 2),
            'open_interest': call_oi,
            'volume': call_volume,
            'oi_change': int(random.uniform(-50000, 50000)),
        })
        
        # Put option
        put_iv = base_iv + random.uniform(-0.02, 0.02)
        put_price = max(0.05, black_scholes_put(spot_price, strike, days_to_expiry/365, 0.06, put_iv))
        put_oi = int(random.uniform(10000, 500000) * math.exp(-abs(moneyness) * 3))
        put_volume = int(put_oi * random.uniform(0.1, 0.5))
        
        puts.append({
            'strike': strike,
            'last': round(put_price, 2),
            'bid': round(put_price * 0.98, 2),
            'ask': round(put_price * 1.02, 2),
            'iv': round(put_iv, 4),
            'delta': round(calculate_delta(spot_price, strike, days_to_expiry/365, 0.06, put_iv, 'put'), 4),
            'gamma': round(random.uniform(0.001, 0.01), 4),
            'theta': round(-random.uniform(0.5, 5), 2),
            'vega': round(random.uniform(5, 20), 2),
            'open_interest': put_oi,
            'volume': put_volume,
            'oi_change': int(random.uniform(-50000, 50000)),
        })
    
    # Calculate PCR
    total_put_oi = sum(p['open_interest'] for p in puts)
    total_call_oi = sum(c['open_interest'] for c in calls)
    total_put_vol = sum(p['volume'] for p in puts)
    total_call_vol = sum(c['volume'] for c in calls)
    
    pcr_oi = round(total_put_oi / max(total_call_oi, 1), 4)
    pcr_volume = round(total_put_vol / max(total_call_vol, 1), 4)
    
    # Find ATM straddle price
    atm_idx = strikes.index(atm_strike)
    atm_straddle = calls[atm_idx]['last'] + puts[atm_idx]['last']
    
    # Calculate max pain
    max_pain_strike = calculate_max_pain(calls, puts, strikes)
    
    return {
        'product': product,
        'expiry': expiry,
        'spot_price': round(spot_price, 2),
        'strikes': strikes,
        'calls': calls,
        'puts': puts,
        'pcr_oi': pcr_oi,
        'pcr_volume': pcr_volume,
        'atm_strike': atm_strike,
        'atm_straddle_price': round(atm_straddle, 2),
        'max_pain_strike': max_pain_strike,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

def black_scholes_call(S, K, T, r, sigma):
    """Simple Black-Scholes call option pricing."""
    if T <= 0 or sigma <= 0:
        return max(0, S - K)
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

def black_scholes_put(S, K, T, r, sigma):
    """Simple Black-Scholes put option pricing."""
    if T <= 0 or sigma <= 0:
        return max(0, K - S)
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def norm_cdf(x):
    """Standard normal cumulative distribution function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def calculate_delta(S, K, T, r, sigma, option_type):
    """Calculate option delta."""
    if T <= 0 or sigma <= 0:
        if option_type == 'call':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    
    if option_type == 'call':
        return norm_cdf(d1)
    else:
        return norm_cdf(d1) - 1

def calculate_max_pain(calls, puts, strikes):
    """Calculate max pain strike."""
    min_pain = float('inf')
    max_pain_strike = strikes[len(strikes) // 2]
    
    for expiry_strike in strikes:
        total_pain = 0
        
        for call in calls:
            if expiry_strike > call['strike']:
                total_pain += call['open_interest'] * (expiry_strike - call['strike'])
        
        for put in puts:
            if expiry_strike < put['strike']:
                total_pain += put['open_interest'] * (put['strike'] - expiry_strike)
        
        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = expiry_strike
    
    return max_pain_strike

def update_prices():
    """Update simulated prices with small random changes."""
    for product in PRODUCTS:
        base = BASE_PRICES.get(product, 100)
        if product not in price_store:
            price_store[product] = base
        
        # Random walk
        change = price_store[product] * random.uniform(-0.001, 0.001)
        price_store[product] = max(base * 0.9, min(base * 1.1, price_store[product] + change))

# Initialize prices
for product in PRODUCTS:
    price_store[product] = BASE_PRICES.get(product, 100) * (1 + random.uniform(-0.01, 0.01))

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print(f"Starting DeltaStream Dashboard Backend")
    print(f"MongoDB URL: {MONGO_URL}")
    yield
    # Shutdown
    print("Shutting down DeltaStream Dashboard Backend")

app = FastAPI(
    title="DeltaStream Dashboard API",
    description="REST API for DeltaStream Dashboard - Real-time Option Trading Analytics",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "deltastream-dashboard"}

@app.get("/api/data/products")
async def get_products():
    """Get available products."""
    return {"products": PRODUCTS}

@app.get("/api/data/underlying/{product}")
async def get_underlying(product: str, limit: int = Query(default=100, ge=1, le=1000)):
    """Get underlying price ticks."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product} not found")
    
    update_prices()
    
    # Generate price history
    ticks = []
    current_price = price_store[product]
    
    for i in range(limit):
        timestamp = datetime.utcnow() - timedelta(seconds=i)
        price_variation = current_price * random.uniform(-0.0005, 0.0005) * (limit - i) / limit
        ticks.append({
            'id': str(uuid.uuid4()),
            'product': product,
            'price': round(current_price + price_variation, 2),
            'timestamp': timestamp.isoformat() + 'Z'
        })
    
    return {
        'product': product,
        'count': len(ticks),
        'ticks': list(reversed(ticks))
    }

@app.get("/api/data/chain/{product}")
async def get_chain(product: str, expiry: Optional[str] = None, limit: int = Query(default=1, ge=1, le=10)):
    """Get option chains."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product} not found")
    
    update_prices()
    
    chain = generate_option_chain(product, price_store[product])
    
    return {
        'product': product,
        'count': 1,
        'chains': [chain]
    }

@app.get("/api/data/expiries/{product}")
async def get_expiries(product: str):
    """Get expiry dates for product."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product} not found")
    
    return {
        'product': product,
        'expiries': generate_expiries()
    }

@app.get("/api/analytics/pcr/{product}")
async def get_pcr(product: str, history: bool = Query(default=False)):
    """Get PCR analysis."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product} not found")
    
    update_prices()
    chain = generate_option_chain(product, price_store[product])
    
    latest = {
        'product': product,
        'pcr_oi': chain['pcr_oi'],
        'pcr_volume': chain['pcr_volume'],
        'spot_price': chain['spot_price'],
        'timestamp': chain['timestamp']
    }
    
    result = {'product': product, 'latest': latest}
    
    if history:
        # Generate historical PCR data
        history_data = []
        for i in range(24):
            timestamp = datetime.utcnow() - timedelta(hours=i)
            history_data.append({
                'pcr_oi': round(chain['pcr_oi'] + random.uniform(-0.2, 0.2), 4),
                'pcr_volume': round(chain['pcr_volume'] + random.uniform(-0.2, 0.2), 4),
                'spot_price': round(chain['spot_price'] * (1 + random.uniform(-0.02, 0.02)), 2),
                'timestamp': timestamp.isoformat() + 'Z'
            })
        result['history'] = list(reversed(history_data))
    
    return result

@app.get("/api/analytics/volatility-surface/{product}")
async def get_volatility_surface(product: str):
    """Get volatility surface."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product} not found")
    
    update_prices()
    spot = price_store[product]
    interval = STRIKE_INTERVALS.get(product, 50)
    atm = round(spot / interval) * interval
    
    expiries_data = []
    expiry_dates = generate_expiries()[:5]  # Use first 5 expiries
    
    for expiry in expiry_dates:
        days = max(1, (datetime.strptime(expiry, '%Y-%m-%d') - datetime.now()).days)
        
        strikes = [atm + (i - 7) * interval for i in range(15)]
        call_ivs = []
        put_ivs = []
        
        for strike in strikes:
            moneyness = (strike - spot) / spot
            base_iv = 0.12 + abs(moneyness) * 0.4 + days * 0.001
            call_ivs.append(round(base_iv + random.uniform(-0.01, 0.01), 4))
            put_ivs.append(round(base_iv + random.uniform(-0.01, 0.01), 4))
        
        expiries_data.append({
            'expiry': expiry,
            'days_to_expiry': days,
            'strikes': strikes,
            'call_ivs': call_ivs,
            'put_ivs': put_ivs,
            'avg_iv': round(sum(call_ivs) / len(call_ivs), 4)
        })
    
    return {
        'product': product,
        'spot_price': round(spot, 2),
        'expiries': expiries_data,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

@app.get("/api/analytics/max-pain/{product}")
async def get_max_pain(product: str, expiry: Optional[str] = None):
    """Get max pain analysis."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product} not found")
    
    update_prices()
    chain = generate_option_chain(product, price_store[product])
    
    return {
        'product': product,
        'expiry': chain['expiry'],
        'spot_price': chain['spot_price'],
        'max_pain_strike': chain['max_pain_strike'],
        'distance_from_spot': round((chain['max_pain_strike'] - chain['spot_price']) / chain['spot_price'] * 100, 2),
        'timestamp': chain['timestamp']
    }

@app.get("/api/analytics/oi-buildup/{product}")
async def get_oi_buildup(product: str, expiry: Optional[str] = None):
    """Get OI build-up analysis."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product} not found")
    
    update_prices()
    chain = generate_option_chain(product, price_store[product])
    
    # Generate OI build-up data
    buildup = []
    for i, strike in enumerate(chain['strikes']):
        call_oi_change = chain['calls'][i]['oi_change']
        put_oi_change = chain['puts'][i]['oi_change']
        
        # Determine build-up type
        call_type = 'long_buildup' if call_oi_change > 0 else 'long_unwinding'
        put_type = 'short_buildup' if put_oi_change > 0 else 'short_covering'
        
        buildup.append({
            'strike': strike,
            'call_oi_change': call_oi_change,
            'put_oi_change': put_oi_change,
            'call_buildup_type': call_type,
            'put_buildup_type': put_type
        })
    
    return {
        'product': product,
        'expiry': chain['expiry'],
        'spot_price': chain['spot_price'],
        'buildup': buildup,
        'timestamp': chain['timestamp']
    }

@app.get("/api/analytics/ohlc/{product}")
async def get_ohlc(product: str, window: int = Query(default=5, ge=1, le=60)):
    """Get OHLC data."""
    if product not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product {product} not found")
    
    update_prices()
    current = price_store[product]
    
    # Generate OHLC candles
    candles = []
    for i in range(24):
        timestamp = datetime.utcnow() - timedelta(minutes=i * window)
        base = current * (1 + random.uniform(-0.02, 0.02) * (24 - i) / 24)
        open_price = base * (1 + random.uniform(-0.005, 0.005))
        close_price = base * (1 + random.uniform(-0.005, 0.005))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.003))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.003))
        
        candles.append({
            'timestamp': timestamp.isoformat() + 'Z',
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': random.randint(10000, 100000)
        })
    
    return {
        'product': product,
        'window': window,
        'candles': list(reversed(candles))
    }

# Auth endpoints (mock)
@app.post("/api/auth/login")
async def login(data: dict):
    """Mock login endpoint."""
    return {
        'token': f"mock_token_{uuid.uuid4().hex[:16]}",
        'user': {
            'email': data.get('email', 'user@example.com'),
            'name': 'Demo User'
        }
    }

@app.post("/api/auth/register")
async def register(data: dict):
    """Mock register endpoint."""
    return {
        'token': f"mock_token_{uuid.uuid4().hex[:16]}",
        'user': {
            'email': data.get('email', 'user@example.com'),
            'name': data.get('name', 'Demo User')
        }
    }

@app.post("/api/auth/verify")
async def verify():
    """Mock verify endpoint."""
    return {'valid': True}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8001)
