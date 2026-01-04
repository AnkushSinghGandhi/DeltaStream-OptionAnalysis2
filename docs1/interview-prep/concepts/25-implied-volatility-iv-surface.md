### **25. IMPLIED VOLATILITY (IV) SURFACE**

**What it is:**
3D representation of implied volatility across strikes and expiries.

**Dimensions:**
- X-axis: Strike price
- Y-axis: Time to expiry
- Z-axis: Implied volatility

**In your code:**
```python
surface = {
    'product': 'NIFTY',
    'expiries': [
        {
            'expiry': '2025-01-25',
            'strikes': [21000, 21500, 22000],
            'ivs': [0.25, 0.20, 0.23],  # Higher IV at extremes (smile)
        },
        {
            'expiry': '2025-02-28',
            'strikes': [21000, 21500, 22000],
            'ivs': [0.22, 0.18, 0.20],
        }
    ]
}
```

**Why it matters:**
- **Volatility smile**: OTM options have higher IV
- **Volatility skew**: Puts have higher IV than calls (fear premium)
- **Arbitrage**: Identify mispriced options
- **Risk management**: Understand portfolio volatility exposure

---
