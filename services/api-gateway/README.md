# API Gateway Service

## Overview

Central REST API gateway providing unified interface to all backend services.

## Base URL

Local: `http://localhost:8000`

## API Documentation

OpenAPI spec available at: `GET /api/docs`

## Endpoints

### Authentication
- `POST /api/auth/register` - Register user
- `POST /api/auth/login` - Login user
- `POST /api/auth/verify` - Verify token

### Data
- `GET /api/data/products` - List products
- `GET /api/data/underlying/{product}` - Get price ticks
- `GET /api/data/chain/{product}` - Get option chains
- `GET /api/data/expiries/{product}` - Get expiries

### Analytics
- `GET /api/analytics/pcr/{product}` - PCR analysis
- `GET /api/analytics/volatility-surface/{product}` - IV surface
- `GET /api/analytics/max-pain/{product}` - Max pain analysis

## Usage Examples

```bash
# Get products
curl http://localhost:8000/api/data/products

# Get NIFTY ticks
curl "http://localhost:8000/api/data/underlying/NIFTY?limit=10"

# Get PCR
curl http://localhost:8000/api/analytics/pcr/NIFTY
```
