# DeltaStream Dashboard Frontend

**Modern React dashboard for real-time options analytics and paper trading**

## Features

### ✅ Real-time Data Visualization
- Live price charts with WebSocket integration
- PCR (Put-Call Ratio) trend analysis
- Implied Volatility Surface 3D visualization
- Open Interest heatmaps
- Max Pain analysis charts

### ✅ Option Chain Analysis
- Real-time option chain table
- ATM/OTM/ITM strike highlighting
- Delta, Gamma, Theta display
- IV smile charts

### ✅ Paper Trading
- Virtual trading with realistic order book matching
- Market & Limit orders
- Portfolio P&L tracking
- Position management
- Order history

### ✅ User Interface
- Responsive dark theme
- 6 analytics tabs
- Multi-product selector (NIFTY, BANKNIFTY, etc.)
- Login/Register authentication
- Real-time connection status

## Technology Stack

- **React** 18.2 - UI framework
- **Recharts** - Charts library
- **Socket.IO Client** - WebSocket connection
- **Axios** - HTTP requests
- **Lucide React** - Icons

## Project Structure

```
dashboard-frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Charts.js           # 6 chart components
│   │   ├── OptionChainTable.js # Option chain display
│   │   ├── MetricsCards.js     # Summary cards
│   │   ├── LiveTicker.js       # Scrolling price ticker
│   │   ├── IVSurface.js        # 3D IV surface
│   │   ├── OIHeatmap.js        # OI concentration heatmap
│   │   ├── LoginPage.js        # Auth page
│   │   └── Trading.js          # Trading interface
│   ├── hooks/
│   │   └── useSocket.js        # WebSocket hook
│   ├── services/
│   │   └── api.js              # API client
│   ├── App.js                  # Main app
│   ├── index.js                # Entry point
│   └── index.css               # Styles
├── package.json
└── README.md
```

## Quick Start

### Install Dependencies
```bash
npm install
```

### Environment Variables
Create `.env` file:
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=http://localhost:8002
```

### Development
```bash
npm start
# Opens http://localhost:3000
```

### Production Build
```bash
npm run build
# Creates optimized build in build/
```

## Components

### 1. App.js (Main)
- Tab navigation (6 tabs)
- Product selector
- WebSocket connection management
- Data state management

### 2. Charts.js
- `PriceChart` - Real-time price line chart
- `PCRChart` - PCR trend with dual axis
- `OIChart` - OI distribution bar chart
- `IVSmileChart` - IV smile curve
- `MaxPainChart` - Max pain calculation visualization
- `StraddleChart` - ATM straddle price trend

### 3. OptionChainTable.js
- Put-Call table with strike prices
- Color-coded by moneyness (ITM/ATM/OTM)
- Sortable columns
- Real-time updates

### 4. MetricsCards.js
- Portfolio summary cards
- P&L metrics
- PCR gauges
- Max Pain indicator

### 5. LiveTicker.js
- Scrolling price ticker for all products
- Auto-updates via WebSocket

### 6. IVSurface.js
- 3D visualization of IV across strikes and expiries
- Interactive rotation

### 7. OIHeatmap.js
- Heatmap of OI concentration by strike
- Identifies key support/resistance

### 8. LoginPage.js
- Email/password authentication
- Register new users
- Demo credentials display

### 9. Trading.js
- Order placement form (Market/Limit)
- Portfolio summary
- Open positions table
- Order history

## API Integration

### REST APIs
```javascript
import * as api from './services/api';

// Data
await api.getProducts();
await api.getOptionChain('NIFTY');

// Trading
await api.placeOrder({ symbol, side, quantity });
await api.getPortfolio();
await api.getPositions();
```

### WebSocket
```javascript
import { useSocket } from './hooks/useSocket';

const { isConnected, prices, chainSummaries, subscribe } = useSocket();

subscribe('NIFTY'); // Subscribe to product
```

## Customization

### Theme Colors
Edit `src/index.css`:
```css
:root {
  --accent-blue: #4dabf7;
  --accent-green: #51cf66;
  --accent-red: #ff6b6b;
  --accent-yellow: #ffd43b;
  --accent-purple: #cc5de8;
}
```

### Add New Tab
1. Add to `TABS` array in `App.js`
2. Add case in `renderTabContent()`
3. Create component if needed

### Add New Chart
1. Create chart component in `components/Charts.js`
2. Import Recharts components
3. Add to tab content

## Performance

- **Chart Optimization**: Limited to last 100 data points
- **WebSocket Batching**: Updates throttled to 100ms
- **Memoization**: React.memo on expensive components
- **Code Splitting**: Lazy loading for heavy components

## Testing

```bash
# Unit tests (if configured)
npm test

# Build test
npm run build

# Serve production build
npx serve -s build
```

## Deployment

### Docker
```bash
docker build -t deltastream-dashboard .
docker run -p 3000:80 deltastream-dashboard
```

### Static Hosting (Netlify/Vercel)
```bash
npm run build
# Deploy build/ folder
```

### Environment Configuration
```javascript
// Set in deployment platform
REACT_APP_API_URL=https://api.deltastream.com
REACT_APP_WS_URL=wss://ws.deltastream.com
```

## Screenshots

### Overview Tab
- Real-time price chart
- PCR trend
- Summary metrics

### Option Chain Tab
- Full option chain with greeks
- ATM strike highlighting

### Analytics Tab
- Straddle price chart
- IV smile

### OI Analysis Tab
- OI distribution bars
- OI heatmap

### IV Surface Tab
- 3D volatility surface
- Interactive controls

### Max Pain Tab
- Max pain calculation chart
- Distance from spot

### Trading Tab (NEW!)
- Order placement
- Portfolio summary
- Positions & orders

## Dependencies

```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "socket.io-client": "^4.5.0",
  "axios": "^1.4.0",
  "recharts": "^2.5.0",
  "lucide-react": "^0.263.1"
}
```

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

Part of DeltaStream Options Trading Platform

---

**Ready to use!** Start with `npm start` and open http://localhost:3000
