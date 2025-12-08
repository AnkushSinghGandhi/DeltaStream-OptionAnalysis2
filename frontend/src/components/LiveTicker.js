import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export function LiveTicker({ prices }) {
  const products = Object.keys(prices);

  if (products.length === 0) {
    return (
      <div className="live-ticker">
        <div className="ticker-item">
          <span className="ticker-symbol">Waiting for data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="live-ticker">
      {products.map((product) => {
        const data = prices[product];
        const change = data.prevPrice
          ? ((data.price - data.prevPrice) / data.prevPrice * 100)
          : 0;
        const isPositive = change > 0;
        const isNegative = change < 0;

        return (
          <div key={product} className="ticker-item">
            <span className="ticker-symbol">{product}</span>
            <span className="ticker-price">
              {data.price?.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
            <span
              className={`ticker-change ${isPositive ? 'positive' : isNegative ? 'negative' : ''}`}
              style={{
                background: isPositive
                  ? 'rgba(0, 214, 143, 0.2)'
                  : isNegative
                  ? 'rgba(255, 107, 107, 0.2)'
                  : 'rgba(160, 160, 176, 0.2)',
                color: isPositive
                  ? 'var(--accent-green)'
                  : isNegative
                  ? 'var(--accent-red)'
                  : 'var(--text-secondary)',
              }}
            >
              {isPositive ? (
                <TrendingUp size={12} />
              ) : isNegative ? (
                <TrendingDown size={12} />
              ) : (
                <Minus size={12} />
              )}
              {Math.abs(change).toFixed(2)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
