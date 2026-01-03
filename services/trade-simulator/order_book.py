#!/usr/bin/env python3
"""
Order Book - Realistic bid/ask spread and depth simulation

Maintains order book for each option symbol with:
- Bid/Ask prices with depth
- Price-time priority matching
- Realistic slippage
"""

import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import structlog

logger = structlog.get_logger()


class OrderBook:
    """Order book for a single symbol"""
    
    def __init__(self, symbol: str, mid_price: float):
        self.symbol = symbol
        self.mid_price = mid_price
        self.bids = []  # [(price, quantity, timestamp), ...]
        self.asks = []  # [(price, quantity, timestamp), ...]
        self.last_trade_price = mid_price
        
        # Initialize with realistic market depth
        self._initialize_depth()
    
    def _initialize_depth(self):
        """Create realistic bid/ask spread with depth"""
        # Typical option spread: 0.5% to 2% of mid price
        spread_pct = random.uniform(0.005, 0.02)
        spread = self.mid_price * spread_pct
        
        # Best bid/ask
        best_bid = self.mid_price - spread / 2
        best_ask = self.mid_price + spread / 2
        
        # Create 5 levels of depth on each side
        levels = 5
        for i in range(levels):
            # Bids (decreasing prices)
            bid_price = best_bid - (i * spread * 0.5)
            bid_qty = random.randint(50, 500)  # Random liquidity
            self.bids.append((bid_price, bid_qty, datetime.now()))
            
            # Asks (increasing prices)
            ask_price = best_ask + (i * spread * 0.5)
            ask_qty = random.randint(50, 500)
            self.asks.append((ask_price, ask_qty, datetime.now()))
        
        # Sort: bids descending, asks ascending
        self.bids.sort(key=lambda x: x[0], reverse=True)
        self.asks.sort(key=lambda x: x[0])
    
    def get_best_bid(self) -> Optional[Tuple[float, int]]:
        """Get best bid price and quantity"""
        if self.bids:
            price, qty, _ = self.bids[0]
            return (price, qty)
        return None
    
    def get_best_ask(self) ->  Optional[Tuple[float, int]]:
        """Get best ask price and quantity"""
        if self.asks:
            price, qty, _ = self.asks[0]
            return (price, qty)
        return None
    
    def get_bid_ask_spread(self) -> float:
        """Get current bid-ask spread"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask[0] - best_bid[0]
        return 0.0
    
    def match_market_buy(self, quantity: int) -> List[Tuple[float, int]]:
        """Match market buy order against asks
        
        Returns list of (price, quantity) fills
        """
        fills = []
        remaining = quantity
        
        while remaining > 0 and self.asks:
            ask_price, ask_qty, ask_time = self.asks[0]
            
            fill_qty = min(remaining, ask_qty)
            fills.append((ask_price, fill_qty))
            
            remaining -= fill_qty
            
            # Update or remove ask level
            if fill_qty < ask_qty:
                self.asks[0] = (ask_price, ask_qty - fill_qty, ask_time)
            else:
                self.asks.pop(0)
        
        # Update last trade price
        if fills:
            self.last_trade_price = fills[-1][0]
        
        return fills
    
    def match_market_sell(self, quantity: int) -> List[Tuple[float, int]]:
        """Match market sell order against bids"""
        fills = []
        remaining = quantity
        
        while remaining > 0 and self.bids:
            bid_price, bid_qty, bid_time = self.bids[0]
            
            fill_qty = min(remaining, bid_qty)
            fills.append((bid_price, fill_qty))
            
            remaining -= fill_qty
            
            # Update or remove bid level
            if fill_qty < bid_qty:
                self.bids[0] = (bid_price, bid_qty - fill_qty, bid_time)
            else:
                self.bids.pop(0)
        
        if fills:
            self.last_trade_price = fills[-1][0]
        
        return fills
    
    def check_limit_buy(self, price: float, quantity: int) -> Optional[List[Tuple[float, int]]]:
        """Check if limit buy can be filled
        
        Returns fills if executable, None otherwise
        """
        best_ask = self.get_best_ask()
        if not best_ask:
            return None
        
        # Limit buy fills if ask <= limit price
        if best_ask[0] <= price:
            # Can fill at market (walk the book)
            fills = []
            remaining = quantity
            
            for ask_price, ask_qty, _ in self.asks:
                if ask_price > price:
                    break  # Can't fill at higher price
                
                fill_qty = min(remaining, ask_qty)
                fills.append((ask_price, fill_qty))
                remaining -= fill_qty
                
                if remaining == 0:
                    break
            
            return fills if fills else None
        
        return None
    
    def check_limit_sell(self, price: float, quantity: int) -> Optional[List[Tuple[float, int]]]:
        """Check if limit sell can be filled"""
        best_bid = self.get_best_bid()
        if not best_bid:
            return None
        
        # Limit sell fills if bid >= limit price
        if best_bid[0] >= price:
            fills = []
            remaining = quantity
            
            for bid_price, bid_qty, _ in self.bids:
                if bid_price < price:
                    break
                
                fill_qty = min(remaining, bid_qty)
                fills.append((bid_price, fill_qty))
                remaining -= fill_qty
                
                if remaining == 0:
                    break
            
            return fills if fills else None
        
        return None
    
    def update_market_price(self, new_mid_price: float):
        """Update order book when market moves"""
        price_change_pct = (new_mid_price - self.mid_price) / self.mid_price
        
        # Shift all bid/ask levels proportionally
        self.bids = [
            (price * (1 + price_change_pct), qty, timestamp)
            for price, qty, timestamp in self.bids
        ]
        
        self.asks = [
            (price * (1 + price_change_pct), qty, timestamp)
            for price, qty, timestamp in self.asks
        ]
        
        self.mid_price = new_mid_price
    
    def get_market_depth(self) -> Dict:
        """Get full order book depth"""
        return {
            'symbol': self.symbol,
            'mid_price': self.mid_price,
            'last_trade': self.last_trade_price,
            'spread': self.get_bid_ask_spread(),
            'bids': [(price, qty) for price, qty, _ in self.bids[:10]],
            'asks': [(price, qty) for price, qty, _ in self.asks[:10]]
        }


class OrderBookManager:
    """Manages order books for all symbols"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.order_books: Dict[str, OrderBook] = {}
        logger.info("order_book_manager_initialized")
    
    def get_or_create_book(self, symbol: str, current_price: float) -> OrderBook:
        """Get existing order book or create new one"""
        if symbol not in self.order_books:
            self.order_books[symbol] = OrderBook(symbol, current_price)
            logger.info("order_book_created", symbol=symbol, price=current_price)
        
        return self.order_books[symbol]
    
    def update_book_price(self, symbol: str, new_price: float):
        """Update order book when market price changes"""
        if symbol in self.order_books:
            self.order_books[symbol].update_market_price(new_price)
    
    def get_market_depth(self, symbol: str) -> Optional[Dict]:
        """Get order book depth for symbol"""
        if symbol in self.order_books:
            return self.order_books[symbol].get_market_depth()
        return None
