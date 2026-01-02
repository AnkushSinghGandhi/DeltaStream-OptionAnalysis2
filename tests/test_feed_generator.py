"""Tests for Feed Generator service."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/feed-generator')))

from datetime import datetime


def test_expiry_date_generation():
    """Test expiry date generation."""
    from app import OptionFeedGenerator
    
    generator = OptionFeedGenerator()
    expiries = generator.generate_expiry_dates('NIFTY')
    
    assert len(expiries) > 0
    assert all(isinstance(exp, str) for exp in expiries)
    # Should be sorted
    assert expiries == sorted(expiries)


def test_strike_price_generation():
    """Test strike price generation."""
    from app import OptionFeedGenerator
    
    generator = OptionFeedGenerator()
    strikes = generator.generate_strike_prices('NIFTY', 21500)
    
    assert len(strikes) > 0
    assert 21500 in strikes  # Spot should be in strikes
    assert all(s > 0 for s in strikes)
    # Should be sorted
    assert strikes == sorted(strikes)


def test_option_price_calculation():
    """Test option pricing."""
    from app import OptionFeedGenerator
    
    generator = OptionFeedGenerator()
    
    # ATM call
    result = generator.calculate_option_price(
        spot=100,
        strike=100,
        option_type='CALL',
        tte=0.25,  # 3 months
        volatility=0.20
    )
    
    assert result['price'] > 0
    assert 0 < result['delta'] < 1
    assert result['gamma'] >= 0
    assert result['vega'] >= 0


def test_underlying_price_update():
    """Test underlying price updates."""
    from app import OptionFeedGenerator
    
    generator = OptionFeedGenerator()
    initial_price = generator.current_prices['NIFTY']
    
    generator.update_underlying_price('NIFTY')
    updated_price = generator.current_prices['NIFTY']
    
    # Price should change (almost certainly)
    # But stay within reasonable bounds
    assert updated_price > initial_price * 0.95
    assert updated_price < initial_price * 1.05
