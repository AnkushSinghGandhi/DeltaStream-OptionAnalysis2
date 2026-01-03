#!/usr/bin/env python3
"""
Portfolio Manager

Handles:
- Position tracking
- P&L calculations (realized & unrealized)
- Portfolio valuation
- Performance metrics
"""

from datetime import datetime, timedelta
from typing import Dict, List
import structlog

logger = structlog.get_logger()


class PortfolioManager:
    """Portfolio and position management"""
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        logger.info("portfolio_manager_initialized")
    
    def get_portfolio(self, user_id: str) -> Dict:
        """Get portfolio summary"""
        portfolio = self.db.portfolios.find_one(
            {'user_id': user_id},
            {'_id': 0}
        )
        
        if not portfolio:
            # Create initial portfolio
            portfolio = self._create_initial_portfolio(user_id)
        
        # Update with latest P&L
        portfolio = self._update_portfolio_pnl(user_id, portfolio)
        
        return portfolio
    
    def get_positions(self, user_id: str) -> List[Dict]:
        """Get all open positions with current P&L"""
        positions = list(self.db.positions.find(
            {'user_id': user_id},
            {'_id': 0}
        ))
        
        # Update each position with current price and P&L
        for position in positions:
            current_price = self._get_current_price(position['symbol'])
            position['current_price'] = current_price
            position['unrealized_pnl'] = self._calculate_unrealized_pnl(position, current_price)
        
        return positions
    
    def get_pnl_summary(self, user_id: str, period: str = 'all') -> Dict:
        """Get P&L summary for period"""
        # Get time filter
        start_time = self._get_period_start(period)
        
        # Realized P&L from closed trades
        realized_pnl = self._calculate_realized_pnl(user_id, start_time)
        
        # Unrealized P&L from open positions
        positions = self.get_positions(user_id)
        unrealized_pnl = sum(p['unrealized_pnl'] for p in positions)
        
        total_pnl = realized_pnl + unrealized_pnl
        
        # Calculate returns
        portfolio = self.get_portfolio(user_id)
        initial_capital = 1000000.0  # 10 lakh
        returns_pct = (total_pnl / initial_capital) * 100
        
        return {
            'period': period,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_pnl,
            'returns_pct': returns_pct,
            'initial_capital': initial_capital,
            'current_value': initial_capital + total_pnl
        }
    
    def get_trade_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        trades = list(self.db.trades.find(
            {'user_id': user_id},
            {'_id': 0}
        ).sort('executed_at', -1).limit(limit))
        
        return trades
    
    def get_performance_metrics(self, user_id: str) -> Dict:
        """Calculate performance metrics"""
        trades = self.get_trade_history(user_id, limit=1000)
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0
            }
        
        # Calculate metrics
        total_trades = len(trades)
        
        # P&L per trade (simplified - assumes paired trades)
        buy_trades = [t for t in trades if t['side'] == 'BUY']
        sell_trades = [t for t in trades if t['side'] == 'SELL']
        
        winning_trades = 0
        total_profit = 0
        total_loss = 0
        
        # Match buy-sell pairs
        for sell in sell_trades:
            matching_buy = next(
                (b for b in buy_trades if b['symbol'] == sell['symbol']),
                None
            )
            if matching_buy:
                pnl = sell['value'] - matching_buy['value'] - sell['commission'] - matching_buy['commission']
                if pnl > 0:
                    winning_trades += 1
                    total_profit += pnl
                else:
                    total_loss += abs(pnl)
        
        num_closed = min(len(buy_trades), len(sell_trades))
        win_rate = (winning_trades / num_closed * 100) if num_closed > 0 else 0
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / (num_closed - winning_trades) if (num_closed - winning_trades) > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        return {
            'total_trades': total_trades,
            'closed_trades': num_closed,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_profit': total_profit,
            'total_loss': total_loss
        }
    
    def _create_initial_portfolio(self, user_id: str) -> Dict:
        """Create initial portfolio with starting capital"""
        portfolio = {
            'user_id': user_id,
            'cash_balance': 1000000.0,  # Rs. 10 lakh
            'margin_used': 0.0,
            'margin_available': 1000000.0,
            'total_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        self.db.portfolios.insert_one(portfolio)
        portfolio.pop('_id', None)
        
        logger.info("initial_portfolio_created", user_id=user_id)
        return portfolio
    
    def _update_portfolio_pnl(self, user_id: str, portfolio: Dict) -> Dict:
        """Update portfolio with latest P&L"""
        # Realized P&L
        realized = self._calculate_realized_pnl(user_id)
        
        # Unrealized P&L from positions
        positions = list(self.db.positions.find({'user_id': user_id}))
        unrealized = 0.0
        
        for position in positions:
            current_price = self._get_current_price(position['symbol'])
            unrealized += self._calculate_unrealized_pnl(position, current_price)
        
        # Update portfolio
        portfolio['realized_pnl'] = realized
        portfolio['unrealized_pnl'] = unrealized
        portfolio['total_pnl'] = realized + unrealized
        
        # Persist to DB
        self.db.portfolios.update_one(
            {'user_id': user_id},
            {'$set': {
                'realized_pnl': realized,
                'unrealized_pnl': unrealized,
                'total_pnl': realized + unrealized,
                'updated_at': datetime.now()
            }}
        )
        
        return portfolio
    
    def _calculate_unrealized_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate mark-to-market P&L for position"""
        quantity = position['quantity']
        entry_price = position['avg_entry_price']
        
        pnl_per_unit = current_price - entry_price
        unrealized_pnl = pnl_per_unit * abs(quantity)
        
        # Adjust sign for short positions
        if quantity < 0:
            unrealized_pnl = -unrealized_pnl
        
        return unrealized_pnl
    
    def _calculate_realized_pnl(self, user_id: str, start_time: datetime = None) -> float:
        """Calculate realized P&L from closed trades"""
        query = {'user_id': user_id}
        if start_time:
            query['executed_at'] = {'$gte': start_time}
        
        trades = list(self.db.trades.find(query))
        
        # Group by symbol to find closed positions
        symbol_trades = {}
        for trade in trades:
            symbol = trade['symbol']
            if symbol not in symbol_trades:
                symbol_trades[symbol] = {'buys': [], 'sells': []}
            
            if trade['side'] == 'BUY':
                symbol_trades[symbol]['buys'].append(trade)
            else:
                symbol_trades[symbol]['sells'].append(trade)
        
        # Calculate P&L for closed positions
        total_realized = 0.0
        
        for symbol, trades_dict in symbol_trades.items():
            buys = trades_dict['buys']
            sells = trades_dict['sells']
            
            # FIFO matching
            for sell in sells:
                sell_qty = sell['quantity']
                sell_value = sell['value']
                
                for buy in buys:
                    if buy.get('matched', 0) >= buy['quantity']:
                        continue  # Fully matched
                    
                    available = buy['quantity'] - buy.get('matched', 0)
                    match_qty = min(sell_qty, available)
                    
                    # Calculate P&L
                    buy_cost = (buy['value'] / buy['quantity']) * match_qty
                    sell_revenue = (sell['value'] / sell['quantity']) * match_qty
                    commission = buy['commission'] + sell['commission']
                    
                    pnl = sell_revenue - buy_cost - commission
                    total_realized += pnl
                    
                    # Mark quantities as matched
                    buy['matched'] = buy.get('matched', 0) + match_qty
                    sell_qty -= match_qty
                    
                    if sell_qty == 0:
                        break
        
        return total_realized
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        import json
        
        # Try Redis cache
        cached = self.redis.get(f"price:{symbol}")
        if cached:
            return float(json.loads(cached))
        
        # Try last trade
        last_trade = self.db.trades.find_one(
            {'symbol': symbol},
            sort=[('executed_at', -1)]
        )
        
        if last_trade:
            return last_trade['price']
        
        # Fallback
        return 100.0
    
    def _get_period_start(self, period: str) -> datetime:
        """Get start time for period"""
        now = datetime.now()
        
        if period == 'today':
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            return now - timedelta(days=7)
        elif period == 'month':
            return now - timedelta(days=30)
        elif period == 'year':
            return now - timedelta(days=365)
        else:  # 'all'
            return datetime(2020, 1, 1)
