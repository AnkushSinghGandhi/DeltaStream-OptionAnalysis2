### **23. PCR (PUT-CALL RATIO)**

**What it is:**
Trading metric comparing put option volume/OI to call option volume/OI.

**Calculation:**
```python
total_call_oi = sum(c['open_interest'] for c in calls)
total_put_oi = sum(p['open_interest'] for p in puts)
pcr = total_put_oi / total_call_oi
```

**Interpretation:**
- PCR > 1.0: More puts than calls (bearish sentiment)
- PCR < 1.0: More calls than puts (bullish sentiment)
- PCR = 0.7-1.0: Typical neutral range

**In trading:**
- Contrarian indicator (high PCR = possible reversal)
- Sentiment gauge (institutional vs retail)

---
