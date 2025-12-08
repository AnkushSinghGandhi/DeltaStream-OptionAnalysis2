import React, { useMemo } from 'react';

export function OptionChainTable({ chainData, spotPrice }) {
  // Extract data with fallbacks
  const calls = chainData?.calls || [];
  const puts = chainData?.puts || [];
  const strikes = chainData?.strikes || [];

  // Find ATM strike - hooks must be called unconditionally
  const atmStrike = useMemo(() => {
    if (!strikes || strikes.length === 0) return null;
    return strikes.reduce((prev, curr) =>
      Math.abs(curr - spotPrice) < Math.abs(prev - spotPrice) ? curr : prev
    );
  }, [strikes, spotPrice]);

  // Create rows matching calls and puts by strike
  const rows = useMemo(() => {
    if (!calls.length || !puts.length || !strikes.length) return [];
    
    const callMap = new Map(calls.map(c => [c.strike, c]));
    const putMap = new Map(puts.map(p => [p.strike, p]));
    
    return strikes.map(strike => ({
      strike,
      call: callMap.get(strike),
      put: putMap.get(strike),
      isATM: strike === atmStrike,
    }));
  }, [calls, puts, strikes, atmStrike]);

  // Early return after hooks
  if (!chainData || !chainData.calls || !chainData.puts) {
    return <div className="loading">No option chain data available</div>;
  }

  const formatNumber = (num, decimals = 2) => {
    if (num === undefined || num === null) return '-';
    return num.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  };

  const formatOI = (num) => {
    if (num === undefined || num === null) return '-';
    if (num >= 100000) return `${(num / 100000).toFixed(2)}L`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatIV = (num) => {
    if (num === undefined || num === null) return '-';
    return `${(num * 100).toFixed(1)}%`;
  };

  return (
    <div className="option-chain-container">
      <table className="option-chain-table">
        <thead>
          <tr>
            <th colSpan="6" style={{ textAlign: 'center', background: 'rgba(0, 214, 143, 0.2)' }}>
              CALLS
            </th>
            <th style={{ background: '#252540' }}>STRIKE</th>
            <th colSpan="6" style={{ textAlign: 'center', background: 'rgba(255, 107, 107, 0.2)' }}>
              PUTS
            </th>
          </tr>
          <tr>
            {/* Call headers */}
            <th className="call-side">OI</th>
            <th className="call-side">Volume</th>
            <th className="call-side">IV</th>
            <th className="call-side">Bid</th>
            <th className="call-side">Ask</th>
            <th className="call-side">LTP</th>
            {/* Strike */}
            <th className="strike-col">Strike</th>
            {/* Put headers */}
            <th className="put-side">LTP</th>
            <th className="put-side">Bid</th>
            <th className="put-side">Ask</th>
            <th className="put-side">IV</th>
            <th className="put-side">Volume</th>
            <th className="put-side">OI</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.strike} className={row.isATM ? 'atm-row' : ''}>
              {/* Call data */}
              <td className="call-side">{formatOI(row.call?.open_interest)}</td>
              <td className="call-side">{formatOI(row.call?.volume)}</td>
              <td className="call-side">{formatIV(row.call?.iv)}</td>
              <td className="call-side">{formatNumber(row.call?.bid)}</td>
              <td className="call-side">{formatNumber(row.call?.ask)}</td>
              <td className="call-side" style={{ fontWeight: 600 }}>
                {formatNumber(row.call?.last)}
              </td>
              {/* Strike */}
              <td className="strike-col">{formatNumber(row.strike, 0)}</td>
              {/* Put data */}
              <td className="put-side" style={{ fontWeight: 600 }}>
                {formatNumber(row.put?.last)}
              </td>
              <td className="put-side">{formatNumber(row.put?.bid)}</td>
              <td className="put-side">{formatNumber(row.put?.ask)}</td>
              <td className="put-side">{formatIV(row.put?.iv)}</td>
              <td className="put-side">{formatOI(row.put?.volume)}</td>
              <td className="put-side">{formatOI(row.put?.open_interest)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
