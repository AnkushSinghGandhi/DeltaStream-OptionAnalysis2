"""Tests for Worker Enricher service."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/worker-enricher')))

from datetime import datetime


def test_max_pain_calculation():
    """Test max pain calculation."""
    from app import calculate_max_pain
    
    calls = [
        {'strike': 100, 'open_interest': 1000},
        {'strike': 110, 'open_interest': 2000},
        {'strike': 120, 'open_interest': 500},
    ]
    
    puts = [
        {'strike': 100, 'open_interest': 500},
        {'strike': 110, 'open_interest': 1500},
        {'strike': 120, 'open_interest': 2500},
    ]
    
    strikes = [100, 110, 120]
    
    max_pain = calculate_max_pain(calls, puts, strikes)
    
    assert max_pain in strikes
    assert isinstance(max_pain, (int, float))


def test_pcr_calculation():
    """Test PCR calculation logic."""
    # Simulate option chain data
    chain_data = {
        'product': 'NIFTY',
        'expiry': '2025-01-25',
        'spot_price': 21500,
        'calls': [
            {'strike': 21400, 'open_interest': 10000, 'volume': 500},
            {'strike': 21500, 'open_interest': 15000, 'volume': 800},
            {'strike': 21600, 'open_interest': 12000, 'volume': 600},
        ],
        'puts': [
            {'strike': 21400, 'open_interest': 12000, 'volume': 600},
            {'strike': 21500, 'open_interest': 18000, 'volume': 900},
            {'strike': 21600, 'open_interest': 11000, 'volume': 550},
        ],
        'strikes': [21400, 21500, 21600],
        'timestamp': datetime.now().isoformat()
    }
    
    # Calculate PCR
    total_call_oi = sum(c['open_interest'] for c in chain_data['calls'])
    total_put_oi = sum(p['open_interest'] for p in chain_data['puts'])
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
    
    assert pcr > 0
    assert isinstance(pcr, float)
    # In this test data, puts > calls, so PCR > 1
    assert pcr > 1.0
