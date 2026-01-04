"""
Global Datafeeds Provider

Real market data from Global Datafeeds API.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import structlog
import redis
import gfdlws as gw

# Configuration from environment
GDF_ENDPOINT = os.getenv('GDF_ENDPOINT', 'ws://nimblewebstream.lisuns.com:4575')
GDF_API_KEY = os.getenv('GDF_API_KEY', '')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Market symbols to track
SYMBOLS = os.getenv('GDF_SYMBOLS', os.getenv('SYMBOLS', 'NIFTY,BANKNIFTY')).split(',')
EXCHANGE = os.getenv('EXCHANGE', 'NFO')  # NFO for derivatives, NSE for cash

# Polling interval (seconds)
POLL_INTERVAL = int(os.getenv('GDF_POLL_INTERVAL', os.getenv('POLL_INTERVAL', '5')))

# Logger
logger = structlog.get_logger()


class GlobalDatafeedsProvider:
    """Real-time market data feed using Global Datafeeds API"""
    
    def __init__(self):
        self.logger = logger.bind(provider='globaldatafeeds')
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.connection = None
        self.running = True
        self.current_prices = {}  # Track current spot prices for each symbol
        
        # Validate configuration
        if not GDF_API_KEY:
            raise ValueError("GDF_API_KEY environment variable must be set")
    
    def connect(self):
        """Establish connection to Global Datafeeds"""
        try:
            self.logger.info("connecting_to_gdf", endpoint=GDF_ENDPOINT)
            self.connection = gw.ws.connect(GDF_ENDPOINT, GDF_API_KEY)
            self.logger.info("gdf_connected")
            return True
        except Exception as e:
            self.logger.error("connection_failed", error=str(e))
            return False
    
    def fetch_option_chain(self, underlying: str):
        """
        Fetch complete option chain for underlying
        
        API: lastquoteoptiongreekschain.get(connection, exchange, symbol)
        Returns: Full option chain with Greeks for all strikes and expiries
        """
        try:
            response = gw.lastquoteoptiongreekschain.get(
                self.connection,
                EXCHANGE,
                underlying
            )
            
            data = json.loads(response)
            
            if data.get('Result'):
                self.logger.info(
                    "option_chain_fetched",
                    underlying=underlying,
                    options_count=len(data['Result'])
                )
                return data['Result']
            else:
                self.logger.warning("no_option_chain_data", underlying=underlying)
                return []
                
        except Exception as e:
            self.logger.error(
                "option_chain_fetch_error",
                underlying=underlying,
                error=str(e)
            )
            return []
    
    def fetch_underlying_quote(self, symbols: List[str]):
        """
        Fetch underlying index quotes (NIFTY-I, BANKNIFTY-I)
        
        API: lastquotearray.get(connection, exchange, instruments, onlyLTP)
        """
        try:
            # Format: [{"Value":"NIFTY-I"}, {"Value":"BANKNIFTY-I"}]
            instruments = json.dumps([{"Value": f"{symbol}-I"} for symbol in symbols])
            
            response = gw.lastquotearray.get(
                self.connection,
                EXCHANGE,
                instruments,
                'false'  # Full quote, not just LTP
            )
            
            data = json.loads(response)
            
            if data.get('Result'):
                self.logger.debug(
                    "underlying_quotes_fetched",
                    count=len(data['Result'])
                )
                return data['Result']
            else:
                self.logger.warning("no_underlying_data")
                return []
                
        except Exception as e:
            self.logger.error("underlying_fetch_error", error=str(e))
            return []
    
    def transform_option_data(self, option: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Global Datafeeds option data to DeltaStream format
        
        GDF Format:
        {
            "InstrumentIdentifier": "OPTIDX_NIFTY_25JAN2024_CE_21500",
            "LastTradePrice": 125.50,
            "LastTradeTime": 1704364800,
            "TotalBuyQuantity": 500000,
            "TotalSellQuantity": 450000,
            "OpenInterest": 2500000,
            "IV": 18.5,  # Implied Volatility
            "Delta": 0.55,
            "Gamma": 0.001,
            "Theta": -15.2,
            "Vega": 35.5,
            ...
        }
        """
        instrument_id = option.get('InstrumentIdentifier', '')
        
        return {
            'instrument': instrument_id,
            'price': float(option.get('LastTradePrice', 0)),
            'timestamp': datetime.now().isoformat(),
            'volume': int(option.get('LastTradeQuantity', 0)),
            'oi': int(option.get('OpenInterest', 0)),
            'bid_qty': int(option.get('TotalBuyQuantity', 0)),
            'ask_qty': int(option.get('TotalSellQuantity', 0)),
            'bid': float(option.get('BestBuyPrice', 0)),
            'ask': float(option.get('BestSellPrice', 0)),
            # Greeks
            'iv': float(option.get('IV', 0)),
            'delta': float(option.get('Delta', 0)),
            'gamma': float(option.get('Gamma', 0)),
            'theta': float(option.get('Theta', 0)),
            'vega': float(option.get('Vega', 0)),
            # Additional info
            'exchange': option.get('Exchange', EXCHANGE),
            'last_trade_time': option.get('LastTradeTime'),
        }
    
    def transform_underlying_data(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Transform underlying quote to DeltaStream format"""
        instrument_id = quote.get('InstrumentIdentifier', '')
        
        # Extract symbol (e.g., "NIFTY-I" -> "NIFTY")
        symbol = instrument_id.replace('-I', '') if '-I' in instrument_id else instrument_id
        
        return {
            'product': symbol,
            'price': float(quote.get('LastTradePrice', 0)),
            'timestamp': datetime.now().isoformat(),
            'tick_id': int(datetime.now().timestamp() * 1000),
            'volume': int(quote.get('LastTradeQuantity', 0)),
            'open': float(quote.get('Open', 0)),
            'high': float(quote.get('High', 0)),
            'low': float(quote.get('Low', 0)),
            'close': float(quote.get('Close', 0)),
            'change': float(quote.get('PercentChange', 0)),
        }
    
    def publish_to_redis(self, channel: str, data: Dict[str, Any]):
        """Publish data to Redis channel"""
        try:
            self.redis_client.publish(channel, json.dumps(data))
            self.logger.debug("data_published", channel=channel)
        except Exception as e:
            self.logger.error("redis_publish_error", channel=channel, error=str(e))
    
    def publish_option_chain(self, underlying: str, options: List[Dict]):
        """
        Publish complete option chain
        
        IMPORTANT: Uses 'market:option_chain' channel to match synthetic feed
        """
        try:
            # Transform each option
            transformed_options = []
            for opt in options:
                transformed = self.transform_option_data(opt)
                transformed_options.append(transformed)
            
            # Group by expiry (Global Datafeeds returns all at once)
            # For now, publish all in one chain
            chain_data = {
                'type': 'OPTION_CHAIN',
                'product': underlying,
                'timestamp': datetime.now().isoformat(),
                'expiry': transformed_options[0]['last_trade_time'] if transformed_options else None,
                'spot_price': self.current_prices.get(underlying, 0),
                'strikes': list(set([opt['instrument'].split('_')[-2] for opt in transformed_options if '_' in opt['instrument']])),
                'calls': [opt for opt in transformed_options if 'CE' in opt['instrument']],
                'puts': [opt for opt in transformed_options if 'PE' in opt['instrument']],
            }
            
            # Publish to same channel as synthetic feed
            self.publish_to_redis('market:option_chain', chain_data)
            
            self.logger.info(
                "option_chain_published",
                underlying=underlying,
                options_count=len(options)
            )
        except Exception as e:
            self.logger.error("chain_publish_error", underlying=underlying, error=str(e))
    
    def publish_underlying_quotes(self, quotes: List[Dict]):
        """
        Publish underlying index quotes
        
        IMPORTANT: Uses 'market:underlying' channel to match synthetic feed
        """
        for quote in quotes:
            try:
                transformed = self.transform_underlying_data(quote)
                
                # Match synthetic feed format exactly
                underlying_tick = {
                    'type': 'UNDERLYING',
                    'product': transformed['product'],
                    'price': transformed['price'],
                    'timestamp': transformed['timestamp'],
                    'tick_id': transformed['tick_id'],
                    # Additional real market data
                    'volume': transformed.get('volume', 0),
                    'open': transformed.get('open', 0),
                    'high': transformed.get('high', 0),
                    'low': transformed.get('low', 0),
                    'close': transformed.get('close', 0),
                    'change': transformed.get('change', 0),
                }
                
                # Store current price for chain generation
                self.current_prices[transformed['product']] = transformed['price']
                
                # Publish to same channel as synthetic feed
                self.publish_to_redis('market:underlying', underlying_tick)
                
                self.logger.info(
                    "underlying_published",
                    product=transformed['product'],
                    price=transformed['price']
                )
            except Exception as e:
                self.logger.error("underlying_publish_error", error=str(e))
    
    def run(self):
        """Main loop - fetch and publish market data"""
        self.logger.info("starting_feed_generator", symbols=SYMBOLS)
        
        # Connect to Global Datafeeds
        if not self.connect():
            self.logger.error("initial_connection_failed")
            return
        
        while self.running:
            try:
                # 1. Fetch and publish underlying quotes
                underlying_quotes = self.fetch_underlying_quote(SYMBOLS)
                if underlying_quotes:
                    self.publish_underlying_quotes(underlying_quotes)
                
                # 2. Fetch and publish option chains for each symbol
                for symbol in SYMBOLS:
                    option_chain = self.fetch_option_chain(symbol)
                    if option_chain:
                        self.publish_option_chain(symbol, option_chain)
                
                # Wait before next fetch
                self.logger.debug("waiting", seconds=POLL_INTERVAL)
                time.sleep(POLL_INTERVAL)
                
            except KeyboardInterrupt:
                self.logger.info("shutdown_requested")
                self.running = False
                break
            except Exception as e:
                self.logger.error("loop_error", error=str(e))
                # Try to reconnect
                self.logger.info("attempting_reconnection")
                time.sleep(5)
                self.connect()
