import React from 'react';
import { TrendingUp, TrendingDown, Activity, BarChart3, Target, Layers } from 'lucide-react';

export function MetricsCards({ chainSummary, price }) {
  if (!chainSummary) {
    return null;
  }

  const priceChange = price?.prevPrice 
    ? ((price.price - price.prevPrice) / price.prevPrice * 100).toFixed(2)
    : 0;
  const isPositive = priceChange >= 0;

  const pcrInterpretation = (pcr) => {
    if (pcr > 1.2) return { text: 'Bullish (Contrarian)', color: 'var(--accent-green)' };
    if (pcr > 1) return { text: 'Slightly Bullish', color: 'var(--accent-green)' };
    if (pcr > 0.8) return { text: 'Neutral', color: 'var(--accent-yellow)' };
    if (pcr > 0.6) return { text: 'Slightly Bearish', color: 'var(--accent-red)' };
    return { text: 'Bearish (Contrarian)', color: 'var(--accent-red)' };
  };

  const pcrStatus = pcrInterpretation(chainSummary.pcr_oi);

  return (
    <div className="dashboard-grid">
      {/* Spot Price Card */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            <Activity size={18} />
            Spot Price
          </span>
        </div>
        <div className="price-display">
          <span className={`card-value ${isPositive ? 'positive' : 'negative'}`}>
            {price?.price?.toLocaleString() || chainSummary.spot_price?.toLocaleString()}
          </span>
          <span className={`price-change ${isPositive ? 'positive' : 'negative'}`}>
            {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {priceChange}%
          </span>
        </div>
        <div className="card-subtitle">
          Updated: {price?.timestamp ? new Date(price.timestamp).toLocaleTimeString() : '-'}
        </div>
      </div>

      {/* PCR Card */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            <BarChart3 size={18} />
            Put-Call Ratio (OI)
          </span>
        </div>
        <div className="card-value" style={{ color: pcrStatus.color }}>
          {chainSummary.pcr_oi?.toFixed(4) || '-'}
        </div>
        <div className="card-subtitle" style={{ color: pcrStatus.color }}>
          {pcrStatus.text}
        </div>
      </div>

      {/* ATM Straddle Card */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            <Layers size={18} />
            ATM Straddle
          </span>
        </div>
        <div className="card-value">
          {chainSummary.atm_straddle_price?.toFixed(2) || '-'}
        </div>
        <div className="card-subtitle">
          Expected Move: ±{((chainSummary.atm_straddle_price / chainSummary.spot_price) * 100)?.toFixed(2) || '-'}%
        </div>
      </div>

      {/* Max Pain Card */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            <Target size={18} />
            Max Pain
          </span>
        </div>
        <div className="card-value">
          {chainSummary.max_pain_strike?.toLocaleString() || '-'}
        </div>
        <div className="card-subtitle">
          Distance: {chainSummary.max_pain_strike && chainSummary.spot_price
            ? `${((chainSummary.max_pain_strike - chainSummary.spot_price) / chainSummary.spot_price * 100).toFixed(2)}%`
            : '-'}
        </div>
      </div>
    </div>
  );
}

export function DetailedMetrics({ chainData }) {
  if (!chainData) return null;

  const totalCallOI = chainData.calls?.reduce((sum, c) => sum + c.open_interest, 0) || 0;
  const totalPutOI = chainData.puts?.reduce((sum, p) => sum + p.open_interest, 0) || 0;
  const totalCallVol = chainData.calls?.reduce((sum, c) => sum + c.volume, 0) || 0;
  const totalPutVol = chainData.puts?.reduce((sum, p) => sum + p.volume, 0) || 0;

  const formatLakh = (num) => `${(num / 100000).toFixed(2)}L`;

  return (
    <div className="metrics-grid">
      <div className="metric-item">
        <div className="metric-label">Total Call OI</div>
        <div className="metric-value" style={{ color: 'var(--accent-green)' }}>
          {formatLakh(totalCallOI)}
        </div>
      </div>
      <div className="metric-item">
        <div className="metric-label">Total Put OI</div>
        <div className="metric-value" style={{ color: 'var(--accent-red)' }}>
          {formatLakh(totalPutOI)}
        </div>
      </div>
      <div className="metric-item">
        <div className="metric-label">Call Volume</div>
        <div className="metric-value" style={{ color: 'var(--accent-green)' }}>
          {formatLakh(totalCallVol)}
        </div>
      </div>
      <div className="metric-item">
        <div className="metric-label">Put Volume</div>
        <div className="metric-value" style={{ color: 'var(--accent-red)' }}>
          {formatLakh(totalPutVol)}
        </div>
      </div>
      <div className="metric-item">
        <div className="metric-label">PCR (Volume)</div>
        <div className="metric-value" style={{ color: 'var(--accent-purple)' }}>
          {chainData.pcr_volume?.toFixed(4) || (totalPutVol / totalCallVol).toFixed(4)}
        </div>
      </div>
      <div className="metric-item">
        <div className="metric-label">Expiry</div>
        <div className="metric-value" style={{ color: 'var(--accent-blue)' }}>
          {chainData.expiry || '-'}
        </div>
      </div>
    </div>
  );
}
