#!/bin/bash
# API Examples using curl

BASE_URL="http://localhost:8000"

echo "Option ARO API Examples"
echo "======================"
echo ""

# Health check
echo "1. Health Check:"
curl -s "${BASE_URL}/health" | jq .
echo ""

# Get products
echo "2. Get Products:"
curl -s "${BASE_URL}/api/data/products" | jq .
echo ""

# Get underlying ticks
echo "3. Get NIFTY Underlying Ticks (latest 5):"
curl -s "${BASE_URL}/api/data/underlying/NIFTY?limit=5" | jq .
echo ""

# Get option chain
echo "4. Get NIFTY Option Chain (latest 1):"
curl -s "${BASE_URL}/api/data/chain/NIFTY?limit=1" | jq '.chains[0] | {product, expiry, spot_price, pcr_oi, atm_straddle_price}'
echo ""

# Get expiries
echo "5. Get Available Expiries for NIFTY:"
curl -s "${BASE_URL}/api/data/expiries/NIFTY" | jq .
echo ""

# Get PCR analysis
echo "6. Get PCR Analysis:"
curl -s "${BASE_URL}/api/analytics/pcr/NIFTY" | jq '.latest[0]'
echo ""

# Get volatility surface
echo "7. Get Volatility Surface:"
curl -s "${BASE_URL}/api/analytics/volatility-surface/NIFTY" | jq '{product, num_expiries: (.expiries | length)}'
echo ""

# Register user (example)
echo "8. Register User:"
curl -s -X POST "${BASE_URL}/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}' | jq .
echo ""

echo "Done!"
