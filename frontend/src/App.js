import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  BarChart3,
  TrendingUp,
  Grid3X3,
  Layers,
  Target,
  Wifi,
  WifiOff,
  RefreshCw,
  Database,
} from 'lucide-react';

// Components
import { useSocket } from './hooks/useSocket';
import { PriceChart, PCRChart, OIChart, IVSmileChart, MaxPainChart, StraddleChart } from './components/Charts';
import { OptionChainTable } from './components/OptionChainTable';
import { MetricsCards, DetailedMetrics } from './components/MetricsCards';
import { LiveTicker } from './components/LiveTicker';
import { IVSurface } from './components/IVSurface';
import { OIHeatmap } from './components/OIHeatmap';

// API
import * as api from './services/api';

// Available products
const PRODUCTS = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'AAPL', 'TSLA', 'SPY', 'QQQ'];

// Tabs configuration
const TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'optionchain', label: 'Option Chain', icon: Grid3X3 },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'oi-analysis', label: 'OI Analysis', icon: Layers },
  { id: 'iv-surface', label: 'IV Surface', icon: TrendingUp },
  { id: 'max-pain', label: 'Max Pain', icon: Target },
];

function App() {
  // State
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedProduct, setSelectedProduct] = useState('NIFTY');
  const [priceHistory, setPriceHistory] = useState([]);
  const [pcrHistory, setPcrHistory] = useState([]);
  const [volatilitySurface, setVolatilitySurface] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // REST API data state (fallback when WebSocket not connected)
  const [restPrices, setRestPrices] = useState({});
  const [restChainData, setRestChainData] = useState({});
  const [restChainSummaries, setRestChainSummaries] = useState({});
  const [dataSource, setDataSource] = useState('rest'); // 'websocket' or 'rest'

  // WebSocket hook
  const {
    isConnected,
    prices: wsPrices,
    chainSummaries: wsChainSummaries,
    fullChains: wsFullChains,
    subscribe,
  } = useSocket();

  // Use WebSocket data if connected, otherwise use REST data
  const prices = isConnected ? wsPrices : restPrices;
  const chainSummaries = isConnected ? wsChainSummaries : restChainSummaries;
  const fullChains = isConnected ? wsFullChains : restChainData;

  // Fetch data via REST API
  const fetchRestData = useCallback(async (product) => {
    try {
      // Fetch underlying prices
      const underlyingRes = await api.getUnderlying(product, 50);
      if (underlyingRes.data && underlyingRes.data.ticks) {
        const ticks = underlyingRes.data.ticks;
        const latestTick = ticks[ticks.length - 1];
        
        setRestPrices(prev => ({
          ...prev,
          [product]: {
            price: latestTick?.price,
            timestamp: latestTick?.timestamp,
            prevPrice: ticks.length > 1 ? ticks[ticks.length - 2]?.price : latestTick?.price,
          }
        }));

        // Update price history
        setPriceHistory(ticks.map(t => ({
          time: t.timestamp,
          price: t.price,
        })));
      }

      // Fetch option chain
      const chainRes = await api.getOptionChain(product);
      if (chainRes.data && chainRes.data.chains && chainRes.data.chains[0]) {
        const chain = chainRes.data.chains[0];
        
        setRestChainData(prev => ({
          ...prev,
          [product]: chain
        }));

        setRestChainSummaries(prev => ({
          ...prev,
          [product]: {
            product: chain.product,
            expiry: chain.expiry,
            spot_price: chain.spot_price,
            pcr_oi: chain.pcr_oi,
            pcr_volume: chain.pcr_volume,
            atm_straddle_price: chain.atm_straddle_price,
            max_pain_strike: chain.max_pain_strike,
            timestamp: chain.timestamp,
          }
        }));

        // Update PCR history
        setPcrHistory(prev => {
          const newEntry = {
            time: chain.timestamp,
            pcr_oi: chain.pcr_oi,
            pcr_volume: chain.pcr_volume,
            spot_price: chain.spot_price,
          };
          // Keep last 50 entries and add new one
          const updated = [...prev.slice(-49), newEntry];
          return updated;
        });
      }
    } catch (err) {
      console.error('Failed to fetch REST data:', err);
    }
  }, []);

  // Initial data fetch and periodic refresh via REST
  useEffect(() => {
    // Fetch data immediately
    fetchRestData(selectedProduct);
    
    // Set up periodic refresh every 3 seconds if not connected to WebSocket
    const interval = setInterval(() => {
      if (!isConnected) {
        fetchRestData(selectedProduct);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [selectedProduct, isConnected, fetchRestData]);

  // Subscribe to products on mount and when selected product changes (WebSocket)
  useEffect(() => {
    if (isConnected) {
      subscribe(selectedProduct);
      setDataSource('websocket');
    } else {
      setDataSource('rest');
    }
  }, [isConnected, selectedProduct, subscribe]);

  // Update price history when new prices come in
  useEffect(() => {
    const currentPrice = prices[selectedProduct];
    if (currentPrice) {
      setPriceHistory(prev => {
        const newHistory = [...prev, {
          time: currentPrice.timestamp,
          price: currentPrice.price,
        }];
        // Keep last 100 points
        return newHistory.slice(-100);
      });
    }
  }, [prices, selectedProduct]);

  // Update PCR history when new chain summaries come in
  useEffect(() => {
    const currentSummary = chainSummaries[selectedProduct];
    if (currentSummary) {
      setPcrHistory(prev => {
        const newHistory = [...prev, {
          time: currentSummary.timestamp,
          pcr_oi: currentSummary.pcr_oi,
          pcr_volume: currentSummary.pcr_volume,
          spot_price: currentSummary.spot_price,
        }];
        return newHistory.slice(-50);
      });
    }
  }, [chainSummaries, selectedProduct]);

  // Fetch volatility surface
  const fetchVolatilitySurface = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.getVolatilitySurface(selectedProduct);
      setVolatilitySurface(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch volatility surface:', err);
      setError('Failed to fetch volatility surface');
    } finally {
      setLoading(false);
    }
  }, [selectedProduct]);

  // Fetch data when tab changes
  useEffect(() => {
    if (activeTab === 'iv-surface') {
      fetchVolatilitySurface();
    }
  }, [activeTab, fetchVolatilitySurface]);

  // Reset history when product changes
  useEffect(() => {
    setPriceHistory([]);
    setPcrHistory([]);
    setVolatilitySurface(null);
  }, [selectedProduct]);

  // Get current data
  const currentPrice = prices[selectedProduct];
  const currentChainSummary = chainSummaries[selectedProduct];
  const currentFullChain = fullChains[selectedProduct];

  // Render tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <>
            {/* Metrics Cards */}
            <MetricsCards
              chainSummary={currentChainSummary}
              price={currentPrice}
            />

            {/* Price Chart */}
            <div className="card card-full" style={{ marginTop: '1.5rem' }}>
              <div className="card-header">
                <span className="card-title">
                  <TrendingUp size={18} />
                  Price Movement
                </span>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  Last {priceHistory.length} ticks
                </span>
              </div>
              <div className="chart-container">
                {priceHistory.length > 0 ? (
                  <PriceChart data={priceHistory} />
                ) : (
                  <div className="loading">Waiting for price data...</div>
                )}
              </div>
            </div>

            {/* PCR Chart */}
            <div className="card card-full" style={{ marginTop: '1.5rem' }}>
              <div className="card-header">
                <span className="card-title">
                  <BarChart3 size={18} />
                  PCR Trend
                </span>
              </div>
              <div className="chart-container">
                {pcrHistory.length > 0 ? (
                  <PCRChart data={pcrHistory} />
                ) : (
                  <div className="loading">Waiting for PCR data...</div>
                )}
              </div>
            </div>
          </>
        );

      case 'optionchain':
        return (
          <div className="card card-full">
            <div className="card-header">
              <span className="card-title">
                <Grid3X3 size={18} />
                Option Chain - {selectedProduct}
              </span>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                Expiry: {currentFullChain?.expiry || '-'}
              </span>
            </div>
            {currentFullChain ? (
              <>
                <DetailedMetrics chainData={currentFullChain} />
                <div style={{ marginTop: '1rem' }}>
                  <OptionChainTable
                    chainData={currentFullChain}
                    spotPrice={currentFullChain.spot_price}
                  />
                </div>
              </>
            ) : (
              <div className="loading">
                <div className="loading-spinner" />
                <span style={{ marginLeft: '1rem' }}>Loading option chain...</span>
              </div>
            )}
          </div>
        );

      case 'analytics':
        return (
          <>
            {/* Straddle Chart */}
            <div className="card card-full">
              <div className="card-header">
                <span className="card-title">
                  <Layers size={18} />
                  ATM Straddle Price
                </span>
              </div>
              <div className="chart-container">
                {pcrHistory.length > 0 ? (
                  <StraddleChart
                    data={pcrHistory.map(p => ({
                      time: p.time,
                      straddle: currentChainSummary?.atm_straddle_price || 0,
                    }))}
                  />
                ) : (
                  <div className="loading">Waiting for data...</div>
                )}
              </div>
            </div>

            {/* IV Smile */}
            {currentFullChain && (
              <div className="card card-full" style={{ marginTop: '1.5rem' }}>
                <div className="card-header">
                  <span className="card-title">
                    <TrendingUp size={18} />
                    IV Smile
                  </span>
                </div>
                <div className="chart-container-large">
                  <IVSmileChart
                    data={currentFullChain.strikes.map((strike, idx) => ({
                      strike,
                      call_iv: currentFullChain.calls[idx]?.iv,
                      put_iv: currentFullChain.puts[idx]?.iv,
                    }))}
                  />
                </div>
              </div>
            )}
          </>
        );

      case 'oi-analysis':
        return (
          <>
            {/* OI Distribution Bar Chart */}
            {currentFullChain && (
              <>
                <div className="card card-full">
                  <div className="card-header">
                    <span className="card-title">
                      <BarChart3 size={18} />
                      Open Interest Distribution
                    </span>
                  </div>
                  <div className="chart-container-large">
                    <OIChart
                      calls={currentFullChain.calls.slice(5, 16)}
                      puts={currentFullChain.puts.slice(5, 16)}
                    />
                  </div>
                </div>

                <div className="card card-full" style={{ marginTop: '1.5rem' }}>
                  <div className="card-header">
                    <span className="card-title">
                      <Layers size={18} />
                      OI Heatmap
                    </span>
                  </div>
                  <OIHeatmap chainData={currentFullChain} />
                </div>
              </>
            )}
            {!currentFullChain && (
              <div className="loading">
                <div className="loading-spinner" />
                <span style={{ marginLeft: '1rem' }}>Loading OI data...</span>
              </div>
            )}
          </>
        );

      case 'iv-surface':
        return (
          <div className="card card-full">
            <div className="card-header">
              <span className="card-title">
                <TrendingUp size={18} />
                Implied Volatility Surface
              </span>
              <button
                onClick={fetchVolatilitySurface}
                disabled={loading}
                style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  padding: '0.5rem',
                  cursor: 'pointer',
                  color: 'var(--text-secondary)',
                }}
              >
                <RefreshCw size={16} className={loading ? 'spinning' : ''} />
              </button>
            </div>
            {loading ? (
              <div className="loading">
                <div className="loading-spinner" />
              </div>
            ) : error ? (
              <div className="error-message">{error}</div>
            ) : (
              <IVSurface volatilitySurface={volatilitySurface} />
            )}
          </div>
        );

      case 'max-pain':
        return (
          <>
            {currentFullChain && (
              <>
                <div className="dashboard-grid">
                  <div className="card">
                    <div className="card-header">
                      <span className="card-title">Max Pain Strike</span>
                    </div>
                    <div className="card-value" style={{ color: 'var(--accent-purple)' }}>
                      {currentFullChain.max_pain_strike?.toLocaleString() || currentChainSummary?.max_pain_strike?.toLocaleString()}
                    </div>
                    <div className="card-subtitle">
                      Spot: {currentFullChain.spot_price?.toLocaleString()}
                    </div>
                  </div>
                  <div className="card">
                    <div className="card-header">
                      <span className="card-title">Distance from Spot</span>
                    </div>
                    <div className="card-value">
                      {currentFullChain.max_pain_strike && currentFullChain.spot_price
                        ? `${((currentFullChain.max_pain_strike - currentFullChain.spot_price) / currentFullChain.spot_price * 100).toFixed(2)}%`
                        : '-'}
                    </div>
                    <div className="card-subtitle">
                      {currentFullChain.max_pain_strike > currentFullChain.spot_price
                        ? 'Above Spot (Bullish bias)'
                        : 'Below Spot (Bearish bias)'}
                    </div>
                  </div>
                </div>

                <div className="card card-full" style={{ marginTop: '1.5rem' }}>
                  <div className="card-header">
                    <span className="card-title">
                      <Target size={18} />
                      Max Pain Analysis
                    </span>
                  </div>
                  <div className="chart-container-large">
                    <MaxPainChart
                      calls={currentFullChain.calls}
                      puts={currentFullChain.puts}
                      strikes={currentFullChain.strikes}
                      maxPain={currentFullChain.max_pain_strike || currentChainSummary?.max_pain_strike}
                      spotPrice={currentFullChain.spot_price}
                    />
                  </div>
                  <div style={{ marginTop: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    <p><strong>Max Pain Theory:</strong> The strike price where option writers (sellers) would have maximum profit.</p>
                    <p style={{ marginTop: '0.5rem' }}>
                      <span style={{ color: 'var(--accent-green)', marginRight: '1rem' }}>■ Max Pain Strike</span>
                      <span style={{ color: 'var(--accent-yellow)', marginRight: '1rem' }}>■ Current Spot</span>
                      <span style={{ color: 'var(--accent-blue)' }}>■ Other Strikes</span>
                    </p>
                  </div>
                </div>
              </>
            )}
            {!currentFullChain && (
              <div className="loading">
                <div className="loading-spinner" />
                <span style={{ marginLeft: '1rem' }}>Loading max pain data...</span>
              </div>
            )}
          </>
        );

      default:
        return <div>Select a tab</div>;
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          <Activity size={28} color="#4dabf7" />
          <h1>Option ARO</h1>
        </div>
        <div className="header-status">
          <div className="connection-status">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
            {isConnected ? (
              <>
                <Wifi size={16} />
                <span>Live</span>
              </>
            ) : (
              <>
                <WifiOff size={16} />
                <span>Disconnected</span>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Live Ticker */}
      <div style={{ padding: '0 2rem', background: 'var(--bg-secondary)' }}>
        <LiveTicker prices={prices} />
      </div>

      {/* Navigation */}
      <nav className="nav">
        <div className="nav-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Product Selector */}
      <div style={{ padding: '1rem 2rem', background: 'var(--bg-primary)' }}>
        <div className="product-selector">
          {PRODUCTS.map((product) => (
            <button
              key={product}
              className={`product-btn ${selectedProduct === product ? 'active' : ''}`}
              onClick={() => setSelectedProduct(product)}
            >
              {product}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="main-content">
        {renderTabContent()}
      </main>

      {/* Footer */}
      <footer style={{
        padding: '1rem 2rem',
        background: 'var(--bg-secondary)',
        borderTop: '1px solid var(--border-color)',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        display: 'flex',
        justifyContent: 'space-between',
      }}>
        <span>Option ARO Clone - Real-time Option Analytics Dashboard</span>
        <span>
          {currentChainSummary?.timestamp
            ? `Last Update: ${new Date(currentChainSummary.timestamp).toLocaleString()}`
            : 'Waiting for data...'}
        </span>
      </footer>
    </div>
  );
}

export default App;
