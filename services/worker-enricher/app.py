#!/usr/bin/env python3
"""
Worker Enricher Service

Celery-based worker that:
1. Consumes raw market data from Redis pub/sub
2. Computes enrichments (PCR, straddle prices, build-up analysis, OHLC windows)
3. Persists enriched data to MongoDB
4. Updates Redis cache with latest values
5. Publishes enriched events back to Redis for WebSocket broadcast

Implements:
- Retry logic with exponential backoff
- Idempotency using task IDs
- Dead-letter queue for poison messages
- Structured logging
"""

import os
import json
import redis
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import Celery, Task
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
import math

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/deltastream')
CELERY_BROKER = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'worker-enricher')

# Initialize Celery
celery_app = Celery('worker-enricher', broker=CELERY_BROKER, backend=CELERY_BACKEND)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    # Retry configuration
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3, 'countdown': 5},
    task_default_retry_delay=5,
)

# Database clients (initialized lazily)
mongo_client = None
redis_client = None


def get_mongo_client():
    """Get or create MongoDB client (singleton pattern)."""
    global mongo_client
    if mongo_client is None:
        mongo_client = MongoClient(MONGO_URL)
    return mongo_client


def get_redis_client():
    """Get or create Redis client (singleton pattern)."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return redis_client


class EnrichmentTask(Task):
    """
    Base task class with error handling and logging.
    """
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure - log and send to dead-letter queue."""
        logger.error(
            "task_failed",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            args=args
        )
        
        # Send to dead-letter queue
        redis_client = get_redis_client()
        dlq_message = {
            'task_id': task_id,
            'task_name': self.name,
            'error': str(exc),
            'args': args,
            'timestamp': datetime.now().isoformat()
        }
        redis_client.lpush('dlq:enrichment', json.dumps(dlq_message))


@celery_app.task(base=EnrichmentTask, bind=True)
def process_underlying_tick(self, tick_data: Dict[str, Any]):
    """
    Process underlying price tick.
    
    - Store tick in MongoDB
    - Update Redis cache
    - Calculate and cache OHLC windows
    - Publish enriched tick to WebSocket channel
    
    Args:
        tick_data: Underlying tick dictionary
    """
    try:
        product = tick_data['product']
        price = tick_data['price']
        timestamp = datetime.fromisoformat(tick_data['timestamp'])
        tick_id = tick_data.get('tick_id', 0)
        
        # Idempotency check
        redis_client = get_redis_client()
        idempotency_key = f"processed:underlying:{product}:{tick_id}"
        if redis_client.exists(idempotency_key):
            logger.info("tick_already_processed", product=product, tick_id=tick_id)
            return
        
        # Store in MongoDB
        db = get_mongo_client()['deltastream']
        db.underlying_ticks.insert_one({
            'product': product,
            'price': price,
            'timestamp': timestamp,
            'tick_id': tick_id,
            'processed_at': datetime.now()
        })
        
        # Update Redis cache (latest price)
        redis_client.setex(
            f"latest:underlying:{product}",
            300,  # 5 minute TTL
            json.dumps({'price': price, 'timestamp': tick_data['timestamp']})
        )
        
        # Calculate OHLC windows (1min, 5min, 15min)
        for window_minutes in [1, 5, 15]:
            calculate_ohlc_window.delay(product, window_minutes)
        
        # Mark as processed (TTL 1 hour)
        redis_client.setex(idempotency_key, 3600, '1')
        
        # Publish enriched tick
        enriched = {
            'type': 'UNDERLYING_ENRICHED',
            'product': product,
            'price': price,
            'timestamp': tick_data['timestamp'],
            'processed_at': datetime.now().isoformat()
        }
        redis_client.publish('enriched:underlying', json.dumps(enriched))
        
        logger.info(
            "processed_underlying_tick",
            product=product,
            price=price,
            tick_id=tick_id
        )
        
    except Exception as e:
        logger.error("underlying_tick_processing_error", error=str(e), exc_info=True)
        raise


@celery_app.task(base=EnrichmentTask, bind=True)
def process_option_quote(self, quote_data: Dict[str, Any]):
    """
    Process individual option quote.
    
    - Store quote in MongoDB
    - Update Redis cache
    - Calculate implied volatility surface point
    
    Args:
        quote_data: Option quote dictionary
    """
    try:
        symbol = quote_data['symbol']
        product = quote_data['product']
        
        # Store in MongoDB
        db = get_mongo_client()['deltastream']
        db.option_quotes.insert_one({
            **quote_data,
            'timestamp': datetime.fromisoformat(quote_data['timestamp']),
            'processed_at': datetime.now()
        })
        
        # Update Redis cache (latest quote)
        redis_client = get_redis_client()
        redis_client.setex(
            f"latest:option:{symbol}",
            300,
            json.dumps(quote_data)
        )
        
        # Store for IV surface calculation
        redis_client.zadd(
            f"iv_surface:{product}",
            {json.dumps({'strike': quote_data['strike'], 'iv': quote_data['iv'], 
                        'expiry': quote_data['expiry']}): quote_data['strike']}
        )
        
        logger.info(
            "processed_option_quote",
            symbol=symbol,
            product=product,
            strike=quote_data['strike']
        )
        
    except Exception as e:
        logger.error("option_quote_processing_error", error=str(e), exc_info=True)
        raise


@celery_app.task(base=EnrichmentTask, bind=True)
def process_option_chain(self, chain_data: Dict[str, Any]):
    """
    Process complete option chain.
    
    - Store chain in MongoDB
    - Calculate PCR (Put-Call Ratio)
    - Calculate max pain
    - Identify ATM straddle
    - Calculate total call/put open interest build-up
    - Publish enriched chain
    
    Args:
        chain_data: Option chain dictionary
    """
    try:
        product = chain_data['product']
        expiry = chain_data['expiry']
        spot_price = chain_data['spot_price']
        calls = chain_data['calls']
        puts = chain_data['puts']
        
        # Calculate PCR (Put-Call Ratio)
        total_call_oi = sum(c['open_interest'] for c in calls)
        total_put_oi = sum(p['open_interest'] for p in puts)
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        total_call_volume = sum(c['volume'] for c in calls)
        total_put_volume = sum(p['volume'] for p in puts)
        pcr_volume = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        
        # Find ATM strike
        strikes = sorted(chain_data['strikes'])
        atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
        
        # Get ATM straddle
        atm_call = next((c for c in calls if c['strike'] == atm_strike), None)
        atm_put = next((p for p in puts if p['strike'] == atm_strike), None)
        
        atm_straddle_price = 0
        if atm_call and atm_put:
            atm_straddle_price = atm_call['last'] + atm_put['last']
        
        # Calculate max pain (strike with maximum total writer profit)
        max_pain_strike = calculate_max_pain(calls, puts, strikes)
        
        # Build-up analysis (OI changes - simplified for demo)
        call_buildup = sum(c['open_interest'] for c in calls if c['strike'] > spot_price)
        put_buildup = sum(p['open_interest'] for p in puts if p['strike'] < spot_price)
        
        # Create enriched chain
        enriched_chain = {
            'product': product,
            'expiry': expiry,
            'spot_price': spot_price,
            'pcr_oi': round(pcr, 4),
            'pcr_volume': round(pcr_volume, 4),
            'atm_strike': atm_strike,
            'atm_straddle_price': round(atm_straddle_price, 2),
            'max_pain_strike': max_pain_strike,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'call_buildup_otm': call_buildup,
            'put_buildup_otm': put_buildup,
            'calls': calls,
            'puts': puts,
            'timestamp': chain_data['timestamp'],
            'processed_at': datetime.now().isoformat()
        }
        
        # Store in MongoDB
        db = get_mongo_client()['deltastream']
        db.option_chains.insert_one({
            **enriched_chain,
            'timestamp': datetime.fromisoformat(chain_data['timestamp'])
        })
        
        # Update Redis cache
        redis_client = get_redis_client()
        redis_client.setex(
            f"latest:chain:{product}:{expiry}",
            300,
            json.dumps(enriched_chain)
        )
        
        # Cache PCR for analytics
        redis_client.setex(
            f"latest:pcr:{product}:{expiry}",
            300,
            json.dumps({
                'pcr_oi': round(pcr, 4),
                'pcr_volume': round(pcr_volume, 4),
                'timestamp': chain_data['timestamp']
            })
        )
        
        # Publish enriched chain
        redis_client.publish('enriched:option_chain', json.dumps(enriched_chain))
        
        logger.info(
            "processed_option_chain",
            product=product,
            expiry=expiry,
            pcr=round(pcr, 4),
            atm_straddle=round(atm_straddle_price, 2),
            max_pain=max_pain_strike
        )
        
    except Exception as e:
        logger.error("option_chain_processing_error", error=str(e), exc_info=True)
        raise


def calculate_max_pain(calls: List[Dict], puts: List[Dict], strikes: List[float]) -> float:
    """
    Calculate max pain strike (strike where option writers have maximum profit).
    
    Max pain is the strike price where the total value of outstanding options
    (both calls and puts) is minimized.
    
    Args:
        calls: List of call options
        puts: List of put options
        strikes: List of strike prices
    
    Returns:
        Max pain strike price
    """
    max_pain = strikes[0]
    min_total_value = float('inf')
    
    for strike in strikes:
        # Calculate total value for this strike
        call_value = sum(
            c['open_interest'] * max(0, strike - c['strike'])
            for c in calls
        )
        put_value = sum(
            p['open_interest'] * max(0, p['strike'] - strike)
            for p in puts
        )
        total_value = call_value + put_value
        
        if total_value < min_total_value:
            min_total_value = total_value
            max_pain = strike
    
    return max_pain


@celery_app.task(base=EnrichmentTask, bind=True)
def calculate_ohlc_window(self, product: str, window_minutes: int):
    """
    Calculate OHLC (Open, High, Low, Close) for a time window.
    
    Args:
        product: Product symbol
        window_minutes: Time window in minutes
    """
    try:
        db = get_mongo_client()['deltastream']
        redis_client = get_redis_client()
        
        # Get ticks from last N minutes
        start_time = datetime.now() - timedelta(minutes=window_minutes)
        ticks = list(db.underlying_ticks.find({
            'product': product,
            'timestamp': {'$gte': start_time}
        }).sort('timestamp', ASCENDING))
        
        if not ticks:
            return
        
        # Calculate OHLC
        prices = [t['price'] for t in ticks]
        ohlc = {
            'product': product,
            'window_minutes': window_minutes,
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'start_time': ticks[0]['timestamp'].isoformat(),
            'end_time': ticks[-1]['timestamp'].isoformat(),
            'num_ticks': len(ticks)
        }
        
        # Cache in Redis
        redis_client.setex(
            f"ohlc:{product}:{window_minutes}m",
            window_minutes * 60,
            json.dumps(ohlc)
        )
        
        logger.info(
            "calculated_ohlc",
            product=product,
            window=f"{window_minutes}m",
            ohlc=ohlc
        )
        
    except Exception as e:
        logger.error("ohlc_calculation_error", error=str(e), exc_info=True)
        raise


@celery_app.task(base=EnrichmentTask, bind=True)
def calculate_volatility_surface(self, product: str):
    """
    Calculate implied volatility surface for a product.
    
    Creates a grid of IV values across strikes and expiries.
    
    Args:
        product: Product symbol
    """
    try:
        redis_client = get_redis_client()
        db = get_mongo_client()['deltastream']
        
        # Get recent option quotes
        recent_time = datetime.now() - timedelta(minutes=5)
        quotes = list(db.option_quotes.find({
            'product': product,
            'timestamp': {'$gte': recent_time}
        }))
        
        if not quotes:
            return
        
        # Group by expiry
        expiry_groups = {}
        for quote in quotes:
            expiry = quote['expiry']
            if expiry not in expiry_groups:
                expiry_groups[expiry] = []
            expiry_groups[expiry].append(quote)
        
        # Build surface
        surface = {
            'product': product,
            'expiries': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for expiry, expiry_quotes in expiry_groups.items():
            # Sort by strike
            expiry_quotes.sort(key=lambda x: x['strike'])
            
            strikes = [q['strike'] for q in expiry_quotes]
            ivs = [q['iv'] for q in expiry_quotes]
            
            surface['expiries'].append({
                'expiry': expiry,
                'strikes': strikes,
                'ivs': ivs,
                'avg_iv': sum(ivs) / len(ivs) if ivs else 0
            })
        
        # Cache surface
        redis_client.setex(
            f"volatility_surface:{product}",
            300,
            json.dumps(surface)
        )
        
        logger.info(
            "calculated_volatility_surface",
            product=product,
            num_expiries=len(surface['expiries'])
        )
        
    except Exception as e:
        logger.error("volatility_surface_error", error=str(e), exc_info=True)
        raise


def subscribe_to_feeds():
    """
    Subscribe to Redis pub/sub channels and dispatch tasks.
    
    This runs in the main process and listens to market data feeds,
    dispatching Celery tasks for processing.
    """
    redis_client = get_redis_client()
    pubsub = redis_client.pubsub()
    
    # Subscribe to channels
    pubsub.subscribe('market:underlying', 'market:option_quote', 'market:option_chain')
    
    logger.info("subscribed_to_feeds", channels=['market:underlying', 'market:option_quote', 'market:option_chain'])
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel']
                data = json.loads(message['data'])
                
                # Dispatch to appropriate task
                if channel == 'market:underlying':
                    process_underlying_tick.delay(data)
                elif channel == 'market:option_quote':
                    process_option_quote.delay(data)
                elif channel == 'market:option_chain':
                    process_option_chain.delay(data)
                    # Also trigger volatility surface calculation
                    calculate_volatility_surface.delay(data['product'])
                    
    except KeyboardInterrupt:
        logger.info("subscriber_stopped")
    except Exception as e:
        logger.error("subscriber_error", error=str(e), exc_info=True)
        raise


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'subscribe':
        # Run subscriber in main process
        subscribe_to_feeds()
    else:
        # Run Celery worker
        celery_app.start()
