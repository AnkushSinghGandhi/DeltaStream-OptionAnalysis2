#!/usr/bin/env python3
"""
OMS - Order Management System

Handles:
- Order placement
- Order execution via order book matching
- Order status tracking
- Trade generation
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import structlog

from order_book import OrderBookManager
from rms import RiskManagementSystem

logger = structlog.get_logger()


class OrderManagementSystem:
    """Order lifecycle management"""
    
    def __init__(self, db, redis_client, order_book_manager: OrderBookManager, rms: RiskManagementSystem):
        self.db = db
        self.redis = redis_client
        self.order_book_manager = order_book_manager
        self.rms = rms
        logger.info("oms_initialized")
    
    def place_order(self, user_id: str, order_request: Dict) -> Dict:
        """Place new order with risk checks"""
        # Generate order ID
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"
        
        # Get current market price
        symbol = order_request['symbol']
        current_price = self._get_current_price(symbol)
        
        # Create order object
        order = {
            'order_id': order_id,
            'user_id': user_id,
            'symbol': symbol,
            'product': order_request.get('product', 'NIFTY'),
            'strike': order_request.get('strike'),
            'expiry': order_request.get('expiry'),
            'option_type': order_request.get('option_type'),
            'order_type': order_request['order_type'],  # MARKET, LIMIT
            'side': order_request['side'],  # BUY, SELL
            'quantity': order_request['quantity'],
            'price': order_request.get('price'),  # None for market orders
            'status': 'PENDING',
            'filled_quantity': 0,
            'avg_fill_price': None,
            'placed_at': datetime.now(),
            'filled_at': None,
            'rejection_reason': None
        }
        
        try:
            # Pre-trade risk check
            self.rms.pre_trade_risk_check(user_id, order, current_price)
            
            # Attempt execution
            order = self._execute_order(order, current_price)
            
            # Save order to database
            self.db.orders.insert_one(order)
            
            logger.info("order_placed",
                       order_id=order_id,
                       status=order['status'],
                       user_id=user_id)
            
            return order
            
        except Exception as e:
            # Mark order as rejected
            order['status'] = 'REJECTED'
            order['rejection_reason'] = str(e)
            self.db.orders.insert_one(order)
            
            logger.error("order_rejected",
                        order_id=order_id,
                        reason=str(e),
                        user_id=user_id)
            
            raise
    
    def _execute_order(self, order: Dict, current_price: float) -> Dict:
        """Execute order via order book matching"""
        symbol = order['symbol']
        
        # Get or create order book
        order_book = self.order_book_manager.get_or_create_book(symbol, current_price)
        
        # Match order based on type
        if order['order_type'] == 'MARKET':
            fills = self._execute_market_order(order, order_book)
        else:  # LIMIT
            fills = self._execute_limit_order(order, order_book)
        
        if fills:
            # Calculate average fill price
            total_value = sum(price * qty for price, qty in fills)
            total_qty = sum(qty for _, qty in fills)
            avg_price = total_value / total_qty
            
            # Update order
            order['filled_quantity'] = total_qty
            order['avg_fill_price'] = avg_price
            order['filled_at'] = datetime.now()
            
            if total_qty == order['quantity']:
                order['status'] = 'FILLED'
            else:
                order['status'] = 'PARTIALLY_FILLED'
            
            # Generate trades for each fill
            self._generate_trades(order, fills)
            
            # Update user position
            self._update_position(order)
            
            # Update portfolio
            self._update_portfolio(order)
        
        return order
    
    def _execute_market_order(self, order: Dict, order_book) -> List[Tuple[float, int]]:
        """Execute market order (guaranteed fill)"""
        if order['side'] == 'BUY':
            fills = order_book.match_market_buy(order['quantity'])
        else:
            fills = order_book.match_market_sell(order['quantity'])
        
        logger.info("market_order_executed",
                   order_id=order['order_id'],
                   fills=len(fills))
        
        return fills
    
    def _execute_limit_order(self, order: Dict, order_book) -> List[Tuple[float, int]]:
        """Execute limit order (conditional fill)"""
        if order['side'] == 'BUY':
            fills = order_book.check_limit_buy(order['price'], order['quantity'])
        else:
            fills = order_book.check_limit_sell(order['price'], order['quantity'])
        
        if fills:
            logger.info("limit_order_filled",
                       order_id=order['order_id'],
                       fills=len(fills))
        else:
            logger.info("limit_order_pending",
                       order_id=order['order_id'])
        
        return fills or []
    
    def _generate_trades(self, order: Dict, fills: List[Tuple[float, int]]):
        """Generate trade records for fills"""
        for fill_price, fill_qty in fills:
            trade_id = f"TRD_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"
            
            value = fill_qty * fill_price
            commission = self._calculate_commission(value)
            net_value = value + commission if order['side'] == 'BUY' else value - commission
            
            trade = {
                'trade_id': trade_id,
                'order_id': order['order_id'],
                'user_id': order['user_id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'quantity': fill_qty,
                'price': fill_price,
                'value': value,
                'commission': commission,
                'net_value': net_value,
                'executed_at': datetime.now()
            }
            
            self.db.trades.insert_one(trade)
            
            logger.info("trade_generated",
                       trade_id=trade_id,
                       qty=fill_qty,
                       price=fill_price)
    
    def _update_position(self, order: Dict):
        """Update user position after order fill"""
        position = self.db.positions.find_one({
            'user_id': order['user_id'],
            'symbol': order['symbol']
        })
        
        filled_qty = order['filled_quantity']
        avg_price = order['avg_fill_price']
        
        if position:
            # Existing position - update
            current_qty = position['quantity']
            current_avg = position['avg_entry_price']
            
            if order['side'] == 'BUY':
                new_qty = current_qty + filled_qty
                # Weighted average entry price
                total_cost = (current_qty * current_avg) + (filled_qty * avg_price)
                new_avg = total_cost / new_qty if new_qty > 0 else 0
            else:  # SELL
                new_qty = current_qty - filled_qty
                new_avg = current_avg  # Keep original entry price
            
            if new_qty == 0:
                # Position closed - delete
                self.db.positions.delete_one({'_id': position['_id']})
                logger.info("position_closed", symbol=order['symbol'])
            else:
                # Update position
                self.db.positions.update_one(
                    {'_id': position['_id']},
                    {'$set': {
                        'quantity': new_qty,
                        'avg_entry_price': new_avg,
                        'updated_at': datetime.now()
                    }}
                )
                logger.info("position_updated", symbol=order['symbol'], qty=new_qty)
        
        else:
            # New position - create
            if order['side'] == 'BUY':
                qty = filled_qty
            else:
                qty = -filled_qty  # Negative for short
            
            new_position = {
                'user_id': order['user_id'],
                'symbol': order['symbol'],
                'product': order['product'],
                'strike': order['strike'],
                'expiry': order['expiry'],
                'option_type': order['option_type'],
                'quantity': qty,
                'avg_entry_price': avg_price,
                'current_price': avg_price,
                'unrealized_pnl': 0.0,
                'realized_pnl': 0.0,
                'margin_required': self.rms.calculate_margin(order, avg_price),
                'opened_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            self.db.positions.insert_one(new_position)
            logger.info("position_opened", symbol=order['symbol'], qty=qty)
    
    def _update_portfolio(self, order: Dict):
        """Update portfolio after order fill"""
        portfolio = self.db.portfolios.find_one({'user_id': order['user_id']})
        
        if not portfolio:
            # Create initial portfolio
            portfolio = {
                'user_id': order['user_id'],
                'cash_balance': 1000000.0,  # Initial 10 lakh
                'margin_used': 0.0,
                'margin_available': 1000000.0,
                'total_pnl': 0.0,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0,
                'created_at': datetime.now()
            }
            self.db.portfolios.insert_one(portfolio)
        
        # Calculate impact
        filled_qty = order['filled_quantity']
        avg_price = order['avg_fill_price']
        value = filled_qty * avg_price
        commission = self._calculate_commission(value)
        
        if order['side'] == 'BUY':
            cash_change = -(value + commission)
            margin_change = value
        else:  # SELL
            cash_change = value - commission
            margin_change = self.rms.calculate_margin(order, avg_price)
        
        # Update portfolio
        new_cash = portfolio['cash_balance'] + cash_change
        new_margin_used = portfolio['margin_used'] + margin_change
        new_margin_available = new_cash - new_margin_used
        
        self.db.portfolios.update_one(
            {'user_id': order['user_id']},
            {'$set': {
                'cash_balance': new_cash,
                'margin_used': new_margin_used,
                'margin_available': new_margin_available,
                'updated_at': datetime.now()
            }}
        )
        
        logger.info("portfolio_updated",
                   cash=new_cash,
                   margin_used=new_margin_used)
    
    def cancel_order(self, user_id: str, order_id: str) -> bool:
        """Cancel pending order"""
        order = self.db.orders.find_one({
            'order_id': order_id,
            'user_id': user_id
        })
        
        if not order:
            raise ValueError("Order not found")
        
        if order['status'] != 'PENDING':
            raise ValueError(f"Cannot cancel order in status: {order['status']}")
        
        self.db.orders.update_one(
            {'order_id': order_id},
            {'$set': {'status': 'CANCELLED'}}
        )
        
        logger.info("order_cancelled", order_id=order_id)
        return True
    
    def get_orders(self, user_id: str, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get user orders"""
        query = {'user_id': user_id}
        if status:
            query['status'] = status
        
        orders = list(self.db.orders.find(
            query,
            {'_id': 0}
        ).sort('placed_at', -1).limit(limit))
        
        return orders
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current option price"""
        # Try Redis cache
        import json
        cached = self.redis.get(f"price:{symbol}")
        if cached:
            return float(json.loads(cached))
        
        # Fallback to last trade or default
        last_trade = self.db.trades.find_one(
            {'symbol': symbol},
            sort=[('executed_at', -1)]
        )
        
        return last_trade['price'] if last_trade else 100.0  # Default
    
    def _calculate_commission(self, value: float) -> float:
        """Calculate brokerage commission"""
        # Flat Rs. 20 per trade or 0.05% of value, whichever is lower
        flat_fee = 20.0
        percentage_fee = value * 0.0005
        return min(flat_fee, percentage_fee)
