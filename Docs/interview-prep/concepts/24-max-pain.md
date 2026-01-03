### **24. MAX PAIN**

**What it is:**
Strike price where option writers (sellers) profit the most, and option buyers lose the most.

**Calculation:**
```python
def calculate_max_pain(calls, puts, strikes):
    max_pain = None
    min_total_value = float('inf')
    
    for strike in strikes:
        # Total value of all options at this strike
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
```

**Theory:**
- Market tends to gravitate toward max pain at expiry
- Option writers (market makers) hedge to push price there
- Useful for predicting expiry settlement

---
