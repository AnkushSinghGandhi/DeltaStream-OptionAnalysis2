#!/usr/bin/env python3
"""
RMS - Risk Management System

Pre-trade risk checks:
- Margin requirements
- Position limits
- Order value caps
- Daily loss limits
- Concentration limits
"""

import structlog
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = structlog.get_logger()


class RiskLimitError(Exception):
    """Base exception for risk limit violations"""
    pass


class InsufficientFundsError(RiskLimitError):
    """Insufficient margin available"""
    pass


class PositionLimitError(RiskLimitError):
    """Position limit exceeded"""
    pass


class OrderValueLimitError(RiskLimitError):
    """Order value limit exceeded"""
    pass


class DailyLossLimitError(RiskLimitError):
    """Daily loss limit exceeded"""
    pass


class ConcentrationLimitError(RiskLimitError):
    """Too much exposure to single product"""
    pass


class RiskManagementSystem:
    """Risk management and compliance checks"""
    
    # Risk parameters (configurable per user tier)
    DEFAULT_LIMITS = {
        'max_open_positions': 10,
        'max_order_value': 500000,  # Rs. 5 lakh per order
        'max_portfolio_value': 2000000,  # Rs. 20 lakh total exposure
        'max_loss_per_day': -50000,  # Stop trading if loss > 50k
        'min_cash_balance': 100000,  # Always keep Rs. 1 lakh
        'max_position_concentration': 0.30,  # Max 30% in one product
        'margin_multiplier_buy': 1.0,  # 100% margin for buying
        'margin_multiplier_sell': 5.0,  # 500% margin for selling (SPAN)
    }
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        self.limits = self.DEFAULT_LIMITS.copy()
        logger.info("rms_initialized", limits=self.limits)
    
    def calculate_margin(self, order: Dict, current_price: float) -> float:
        """Calculate margin required for order
        
        Buy: Pay full premium
        Sell: SPAN margin (typically 15-20% of underlying)
        """
        quantity = order['quantity']
        
        if order['side'] == 'BUY':
            # Buying options = premium payment
            if order['order_type'] == 'MARKET':
                price = current_price
            else:
                price = order.get('price', current_price)
            
            margin = quantity * price * self.limits['margin_multiplier_buy']
            return margin
    
        else:  # SELL
            # Selling options = SPAN margin
            # Simplified: 18% of underlying value per lot
            underlying_price = self._get_underlying_price(order['product'])
            lot_size = self._get_lot_size(order['product'])
            margin_per_lot = underlying_price * lot_size * 0.18
            num_lots = quantity / lot_size
            
            margin = margin_per_lot * num_lots * self.limits['margin_multiplier_sell']
            return margin
    
    def pre_trade_risk_check(self, user_id: str, order: Dict, current_price: float) -> bool:
        """Perform all pre-trade risk checks
        
        Raises RiskLimitError if any check fails
        """
        logger.info("pre_trade_check",  user_id=user_id, order_id=order.get('order_id'))
        
        # 1. Check margin availability
        self._check_margin(user_id, order, current_price)
        
        # 2. Check position limits
        self._check_position_limits(user_id, order)
        
        # 3. Check order value
        self._check_order_value(order, current_price)
        
        # 4. Check daily loss limit
        self._check_daily_loss(user_id)
        
        # 5. Check concentration
        self._check_concentration(user_id, order, current_price)
        
        logger.info("risk_check_passed", user_id=user_id, order_id=order.get('order_id'))
        return True
    
    def _check_margin(self, user_id: str, order: Dict, current_price: float):
        """Check if user has sufficient margin"""
        required_margin = self.calculate_margin(order, current_price)
        
        # Get portfolio
        portfolio = self.db.portfolios.find_one({'user_id': user_id})
        if not portfolio:
            raise InsufficientFundsError("Portfolio not found")
        
        available_margin = portfolio.get('margin_available', 0)
        
        if available_margin < required_margin:
            raise InsufficientFundsError(
                f"Insufficient margin. Required: {required_margin:.2f}, "
                f"Available: {available_margin:.2f}"
            )
        
        logger.info("margin_check_passed",
                   required=required_margin,
                   available=available_margin)
    
    def _check_position_limits(self, user_id: str, order: Dict):
        """Check if opening new position would exceed limits"""
        if order['side'] == 'SELL' and not self._has_offsetting_position(user_id, order):
            # Opening new short position
            current_positions = list(self.db.positions.find({'user_id': user_id}))
            
            if len(current_positions) >= self.limits['max_open_positions']:
                raise PositionLimitError(
                    f"Maximum {self.limits['max_open_positions']} positions allowed"
                )
    
    def _check_order_value(self, order: Dict, current_price: float):
        """Check if order value exceeds limit"""
        quantity = order['quantity']
        price = order.get('price', current_price)
        order_value = quantity * price
        
        if order_value > self.limits['max_order_value']:
            raise OrderValueLimitError(
                f"Order value {order_value:.2f} exceeds limit "
                f"{self.limits['max_order_value']:.2f}"
            )
    
    def _check_daily_loss(self, user_id: str):
        """Check if daily loss limit exceeded"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get today's trades
        today_trades = list(self.db.trades.find({
            'user_id': user_id,
            'executed_at': {'$gte': today_start}
        }))
        
        # Calculate realized P&L for today
        realized_pnl = 0
        for trade in today_trades:
            if trade['side'] == 'BUY':
                realized_pnl -= trade['net_value']
            else:
                realized_pnl += trade['net_value']
        
        # Get unrealized P&L
        positions = list(self.db.positions.find({'user_id': user_id}))
        unrealized_pnl = sum(p.get('unrealized_pnl', 0) for p in positions)
        
        total_pnl = realized_pnl + unrealized_pnl
        
        if total_pnl < self.limits['max_loss_per_day']:
            raise DailyLossLimitError(
                f"Daily loss limit {self.limits['max_loss_per_day']} exceeded. "
                f"Current P&L: {total_pnl:.2f}"
            )
    
    def _check_concentration(self, user_id: str, order: Dict, current_price: float):
        """Check if position concentration exceeds limit"""
        product = order['product']
        
        # Get portfolio value
        portfolio = self.db.portfolios.find_one({'user_id': user_id})
        total_value = portfolio.get('cash_balance', 0) + portfolio.get('margin_used', 0)
        
        # Calculate current exposure to this product
        product_positions = list(self.db.positions.find({
            'user_id': user_id,
            'product': product
        }))
        
        current_exposure = sum(
            abs(p['quantity'] * p.get('current_price', p['avg_entry_price']))
            for p in product_positions
        )
        
        # Add this order's value
        order_value = order['quantity'] * current_price
        new_exposure = current_exposure + order_value
        
        concentration = new_exposure / total_value if total_value > 0 else 0
        
        if concentration > self.limits['max_position_concentration']:
            raise ConcentrationLimitError(
                f"Product concentration {concentration:.1%} exceeds limit "
                f"{self.limits['max_position_concentration']:.1%}"
            )
    
    def _has_offsetting_position(self, user_id: str, order: Dict) -> bool:
        """Check if user has opposite position to offset"""
        symbol = order['symbol']
        
        position = self.db.positions.find_one({
            'user_id': user_id,
            'symbol': symbol
        })
        
        if not position:
            return False
        
        # Check if opposite side
        if order['side'] == 'BUY' and position['quantity'] < 0:
            return True
        if order['side'] == 'SELL' and position['quantity'] > 0:
            return True
        
        return False
    
    def _get_underlying_price(self, product: str) -> float:
        """Get current underlying price from cache/DB"""
        # Try Redis cache first
        cache_key = f"latest:underlying:{product}"
        cached = self.redis.get(cache_key)
        
        if cached:
            import json
            data = json.loads(cached)
            return data.get('price', 21500)  # Fallback
        
        # Default fallback
        return 21500 if product == 'NIFTY' else 46000
    
    def _get_lot_size(self, product: str) -> int:
        """Get lot size for product"""
        lot_sizes = {
            'NIFTY': 50,
            'BANKNIFTY': 25,
            'FINNIFTY': 40
        }
        return lot_sizes.get(product, 50)
    
    def get_risk_metrics(self, user_id: str) -> Dict:
        """Get current risk metrics for user"""
        portfolio = self.db.portfolios.find_one({'user_id': user_id})
        positions = list(self.db.positions.find({'user_id': user_id}))
        
        total_value = portfolio.get('cash_balance', 0) + portfolio.get('margin_used', 0)
        
        # Calculate exposure by product
        exposure_by_product = {}
        for pos in positions:
            product = pos['product']
            value = abs(pos['quantity'] * pos.get('current_price', pos['avg_entry_price']))
            exposure_by_product[product] = exposure_by_product.get(product, 0) + value
        
        # Max concentration
        max_concentration = max(
            (exp / total_value for exp in exposure_by_product.values()),
            default=0
        ) if total_value > 0 else 0
        
        return {
            'margin_used': portfolio.get('margin_used', 0),
            'margin_available': portfolio.get('margin_available', 0),
            'margin_utilization': portfolio.get('margin_used', 0) / total_value if total_value > 0 else 0,
            'open_positions': len(positions),
            'max_positions': self.limits['max_open_positions'],
            'total_pnl': portfolio.get('total_pnl', 0),
            'daily_loss_limit': self.limits['max_loss_per_day'],
            'exposure_by_product': exposure_by_product,
            'max_concentration': max_concentration,
            'concentration_limit': self.limits['max_position_concentration']
        }
