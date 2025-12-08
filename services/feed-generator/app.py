#!/usr/bin/env python3
"""
Feed Generator Service

Generates realistic synthetic option market data including:
- Products (underlying symbols)
- Expiry dates
- Strike prices
- Option quotes (call/put, bid/ask, Greeks)
- Option chains
- Underlying price movements

Publishes data to Redis pub/sub for consumption by workers.
"""

import os
import sys
import time
import json
import redis
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import structlog

# Structured logging setup
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
FEED_INTERVAL = float(os.getenv('FEED_INTERVAL', '1'))  # seconds
SERVICE_NAME = os.getenv('SERVICE_NAME', 'feed-generator')

# Market data configuration
PRODUCTS = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'AAPL', 'TSLA', 'SPY', 'QQQ']
BASE_PRICES = {
    'NIFTY': 21500,
    'BANKNIFTY': 45000,
    'FINNIFTY': 19500,
    'SENSEX': 71000,
    'AAPL': 185,
    'TSLA': 245,
    'SPY': 475,
    'QQQ': 395
}


class OptionFeedGenerator:
    """
    Generates realistic option market data feeds.
    
    This class simulates a market data feed by generating:
    - Underlying price ticks with realistic volatility
    - Option chains with multiple strikes and expiries
    - Option quotes with bid/ask spreads and Greeks
    - Time and sales data
    """
    
    def __init__(self):
        """Initialize the feed generator with Redis connection."""
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.current_prices = BASE_PRICES.copy()
        self.logger = logger.bind(service=SERVICE_NAME)
        self.tick_count = 0
        
    def generate_expiry_dates(self, product: str) -> List[str]:
        """
        Generate realistic expiry dates for options.
        
        Returns weekly and monthly expiries for the next 3 months.
        
        Args:
            product: The underlying product symbol
            
        Returns:
            List of expiry dates in YYYY-MM-DD format
        """
        expiries = []
        today = datetime.now()
        
        # Weekly expiries for next 8 weeks
        for week in range(8):
            # Thursday expiry (Indian market convention)
            days_ahead = (3 - today.weekday() + 7 * week) % 7 + 7 * week
            if days_ahead == 0:
                days_ahead = 7
            expiry = today + timedelta(days=days_ahead)
            expiries.append(expiry.strftime('%Y-%m-%d'))
        
        # Monthly expiries
        for month in range(1, 4):
            last_thursday = self._get_last_thursday(today.year, today.month + month)
            if last_thursday > today:
                expiries.append(last_thursday.strftime('%Y-%m-%d'))
        
        return sorted(list(set(expiries)))
    
    def _get_last_thursday(self, year: int, month: int) -> datetime:
        """Get the last Thursday of a given month."""
        if month > 12:
            year += month // 12
            month = month % 12
        
        # Find last day of month
        if month == 12:
            last_day = datetime(year, month, 31)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Find last Thursday
        days_to_thursday = (last_day.weekday() - 3) % 7
        last_thursday = last_day - timedelta(days=days_to_thursday)
        return last_thursday
    
    def generate_strike_prices(self, product: str, spot_price: float) -> List[float]:
        """
        Generate realistic strike prices around the current spot price.
        
        Args:
            product: The underlying product symbol
            spot_price: Current price of the underlying
            
        Returns:
            List of strike prices
        """
        # Determine strike interval based on product
        if product in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            interval = 50 if product == 'NIFTY' else 100
        elif product == 'SENSEX':
            interval = 100
        else:
            interval = 5  # For stocks
        
        # Generate strikes +/- 20% from spot
        strikes = []
        base_strike = round(spot_price / interval) * interval
        
        for i in range(-10, 11):
            strike = base_strike + (i * interval)
            if strike > 0:
                strikes.append(float(strike))
        
        return sorted(strikes)
    
    def calculate_option_price(self, spot: float, strike: float, 
                               option_type: str, tte: float, volatility: float = 0.20) -> Dict[str, float]:
        """
        Calculate option price using simplified Black-Scholes approximation.
        
        This is a simplified model for demo purposes. In production,
        use a proper options pricing library.
        
        Args:
            spot: Current underlying price
            strike: Option strike price
            option_type: 'CALL' or 'PUT'
            tte: Time to expiry in years
            volatility: Implied volatility (annualized)
            
        Returns:
            Dictionary with option price and Greeks
        """
        import math
        
        # Risk-free rate (simplified)
        r = 0.05
        
        # Intrinsic value
        if option_type == 'CALL':
            intrinsic = max(0, spot - strike)
        else:
            intrinsic = max(0, strike - spot)
        
        # Time value (simplified)
        if tte > 0:
            moneyness = spot / strike
            time_value = spot * volatility * math.sqrt(tte) * 0.4
            
            # Adjust for moneyness
            if option_type == 'CALL':
                if moneyness > 1.0:
                    time_value *= (1.2 - 0.2 * (moneyness - 1.0))
                else:
                    time_value *= moneyness
            else:
                if moneyness < 1.0:
                    time_value *= (1.2 - 0.2 * (1.0 - moneyness))
                else:
                    time_value *= (2.0 - moneyness)
        else:
            time_value = 0
        
        option_price = intrinsic + time_value
        
        # Simple Greeks approximation
        delta = 0.5 if abs(spot - strike) < strike * 0.02 else (0.8 if intrinsic > 0 else 0.2)
        if option_type == 'PUT':
            delta = delta - 1
        
        gamma = 0.01 if abs(spot - strike) < strike * 0.02 else 0.005
        vega = spot * math.sqrt(tte) * 0.01 if tte > 0 else 0
        theta = -option_price / (tte * 365) if tte > 0 else 0
        
        return {
            'price': round(option_price, 2),
            'delta': round(delta, 4),
            'gamma': round(gamma, 4),
            'vega': round(vega, 4),
            'theta': round(theta, 4),
            'iv': volatility
        }
    
    def generate_option_quote(self, product: str, spot_price: float, 
                              strike: float, expiry: str, option_type: str) -> Dict[str, Any]:
        """
        Generate a complete option quote with bid/ask spread.
        
        Args:
            product: Underlying symbol
            spot_price: Current underlying price
            strike: Option strike price
            expiry: Expiry date (YYYY-MM-DD)
            option_type: 'CALL' or 'PUT'
            
        Returns:
            Complete option quote dictionary
        """
        # Calculate time to expiry
        expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
        tte = (expiry_date - datetime.now()).days / 365.0
        tte = max(0.001, tte)  # Minimum 1 day
        
        # Calculate option price
        volatility = random.uniform(0.15, 0.35)  # Random IV between 15-35%
        calc = self.calculate_option_price(spot_price, strike, option_type, tte, volatility)
        
        # Add bid/ask spread (0.5-2% of price)
        spread_pct = random.uniform(0.005, 0.02)
        bid_price = calc['price'] * (1 - spread_pct)
        ask_price = calc['price'] * (1 + spread_pct)
        
        # Generate volumes
        volume = random.randint(100, 10000)
        open_interest = random.randint(1000, 100000)
        
        return {
            'symbol': f"{product}{expiry.replace('-', '')}{option_type[0]}{int(strike)}",
            'product': product,
            'strike': strike,
            'expiry': expiry,
            'option_type': option_type,
            'bid': round(bid_price, 2),
            'ask': round(ask_price, 2),
            'last': round(calc['price'], 2),
            'volume': volume,
            'open_interest': open_interest,
            'delta': calc['delta'],
            'gamma': calc['gamma'],
            'vega': calc['vega'],
            'theta': calc['theta'],
            'iv': round(calc['iv'], 4),
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_option_chain(self, product: str, expiry: str) -> Dict[str, Any]:
        """
        Generate a complete option chain for a product and expiry.
        
        Args:
            product: Underlying symbol
            expiry: Expiry date (YYYY-MM-DD)
            
        Returns:
            Complete option chain with calls and puts
        """
        spot_price = self.current_prices[product]
        strikes = self.generate_strike_prices(product, spot_price)
        
        calls = []
        puts = []
        
        for strike in strikes:
            call = self.generate_option_quote(product, spot_price, strike, expiry, 'CALL')
            put = self.generate_option_quote(product, spot_price, strike, expiry, 'PUT')
            calls.append(call)
            puts.append(put)
        
        return {
            'product': product,
            'expiry': expiry,
            'spot_price': spot_price,
            'strikes': strikes,
            'calls': calls,
            'puts': puts,
            'timestamp': datetime.now().isoformat()
        }
    
    def update_underlying_price(self, product: str):
        """
        Update the underlying price with realistic random walk.
        
        Uses geometric Brownian motion to simulate realistic price movements.
        
        Args:
            product: The product symbol to update
        """
        current_price = self.current_prices[product]
        
        # Volatility based on product type
        if product in ['NIFTY', 'SENSEX']:
            volatility = 0.0002  # Lower volatility for indices
        elif product in ['BANKNIFTY', 'FINNIFTY']:
            volatility = 0.0003
        else:
            volatility = 0.0005  # Higher for stocks
        
        # Random price change
        change_pct = random.gauss(0, volatility)
        new_price = current_price * (1 + change_pct)
        
        # Ensure price stays within reasonable bounds
        base_price = BASE_PRICES[product]
        if new_price < base_price * 0.95 or new_price > base_price * 1.05:
            new_price = base_price + random.uniform(-base_price * 0.02, base_price * 0.02)
        
        self.current_prices[product] = round(new_price, 2)
    
    def publish_tick(self, product: str):
        """
        Publish a complete market tick for a product.
        
        Generates and publishes:
        - Underlying price update
        - Option chain for nearest expiry
        - Individual option quotes
        
        Args:
            product: The product to publish data for
        """
        # Update underlying price
        self.update_underlying_price(product)
        spot_price = self.current_prices[product]
        
        # Get expiries
        expiries = self.generate_expiry_dates(product)
        nearest_expiry = expiries[0] if expiries else None
        
        # Publish underlying tick
        underlying_tick = {
            'type': 'UNDERLYING',
            'product': product,
            'price': spot_price,
            'timestamp': datetime.now().isoformat(),
            'tick_id': self.tick_count
        }
        self.redis_client.publish('market:underlying', json.dumps(underlying_tick))
        
        # Every 5 ticks, publish full option chain
        if self.tick_count % 5 == 0 and nearest_expiry:
            option_chain = self.generate_option_chain(product, nearest_expiry)
            self.redis_client.publish('market:option_chain', json.dumps(option_chain))
            
            self.logger.info(
                "published_option_chain",
                product=product,
                expiry=nearest_expiry,
                num_strikes=len(option_chain['strikes']),
                spot_price=spot_price
            )
        
        # Publish individual option quotes for random strikes
        if nearest_expiry:
            strikes = self.generate_strike_prices(product, spot_price)
            sample_strikes = random.sample(strikes, min(3, len(strikes)))
            
            for strike in sample_strikes:
                for option_type in ['CALL', 'PUT']:
                    quote = self.generate_option_quote(product, spot_price, strike, nearest_expiry, option_type)
                    self.redis_client.publish('market:option_quote', json.dumps(quote))
        
        self.tick_count += 1
    
    def run(self):
        """
        Main loop: continuously generate and publish market data.
        """
        self.logger.info(
            "feed_generator_started",
            products=PRODUCTS,
            feed_interval=FEED_INTERVAL
        )
        
        try:
            while True:
                # Publish ticks for all products
                for product in PRODUCTS:
                    self.publish_tick(product)
                
                if self.tick_count % 10 == 0:
                    self.logger.info(
                        "feed_status",
                        tick_count=self.tick_count,
                        current_prices=self.current_prices
                    )
                
                time.sleep(FEED_INTERVAL)
                
        except KeyboardInterrupt:
            self.logger.info("feed_generator_stopped")
        except Exception as e:
            self.logger.error("feed_generator_error", error=str(e), exc_info=True)
            raise


if __name__ == '__main__':
    generator = OptionFeedGenerator()
    generator.run()
