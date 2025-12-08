import React from 'react';

export function OIHeatmap({ chainData }) {
  if (!chainData || !chainData.calls || !chainData.puts) {
    return <div className="loading">No data available</div>;
  }

  const { calls, puts, strikes, spot_price } = chainData;

  // Calculate max OI for normalization
  const maxCallOI = Math.max(...calls.map(c => c.open_interest));
  const maxPutOI = Math.max(...puts.map(p => p.open_interest));
  const maxOI = Math.max(maxCallOI, maxPutOI);

  const getIntensity = (oi) => oi / maxOI;

  const getCallColor = (intensity) => {
    return `rgba(0, 214, 143, ${0.2 + intensity * 0.8})`;
  };

  const getPutColor = (intensity) => {
    return `rgba(255, 107, 107, ${0.2 + intensity * 0.8})`;
  };

  const formatOI = (num) => {
    if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
    if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
    return num.toString();
  };

  // Find ATM index
  const atmIndex = strikes.findIndex(s => 
    Math.abs(s - spot_price) === Math.min(...strikes.map(st => Math.abs(st - spot_price)))
  );

  return (
    <div style={{ display: 'flex', gap: '2rem' }}>
      {/* Call OI Heatmap */}
      <div style={{ flex: 1 }}>
        <h4 style={{ marginBottom: '0.5rem', color: 'var(--accent-green)' }}>Call OI Distribution</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {calls.slice().reverse().map((call, idx) => {
            const intensity = getIntensity(call.open_interest);
            const isATM = (calls.length - 1 - idx) === atmIndex;
            return (
              <div
                key={call.strike}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.25rem 0.5rem',
                  background: getCallColor(intensity),
                  borderRadius: '4px',
                  border: isATM ? '2px solid var(--accent-blue)' : 'none',
                }}
              >
                <span style={{ width: '60px', fontWeight: 600, fontSize: '0.75rem' }}>
                  {call.strike}
                </span>
                <div
                  style={{
                    flex: 1,
                    height: '20px',
                    background: `linear-gradient(90deg, var(--accent-green) ${intensity * 100}%, transparent ${intensity * 100}%)`,
                    borderRadius: '4px',
                  }}
                />
                <span style={{ width: '50px', textAlign: 'right', fontSize: '0.75rem' }}>
                  {formatOI(call.open_interest)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Put OI Heatmap */}
      <div style={{ flex: 1 }}>
        <h4 style={{ marginBottom: '0.5rem', color: 'var(--accent-red)' }}>Put OI Distribution</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {puts.slice().reverse().map((put, idx) => {
            const intensity = getIntensity(put.open_interest);
            const isATM = (puts.length - 1 - idx) === atmIndex;
            return (
              <div
                key={put.strike}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.25rem 0.5rem',
                  background: getPutColor(intensity),
                  borderRadius: '4px',
                  border: isATM ? '2px solid var(--accent-blue)' : 'none',
                }}
              >
                <span style={{ width: '60px', fontWeight: 600, fontSize: '0.75rem' }}>
                  {put.strike}
                </span>
                <div
                  style={{
                    flex: 1,
                    height: '20px',
                    background: `linear-gradient(90deg, var(--accent-red) ${intensity * 100}%, transparent ${intensity * 100}%)`,
                    borderRadius: '4px',
                  }}
                />
                <span style={{ width: '50px', textAlign: 'right', fontSize: '0.75rem' }}>
                  {formatOI(put.open_interest)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
