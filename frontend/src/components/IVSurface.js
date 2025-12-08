import React from 'react';

export function IVSurface({ volatilitySurface }) {
  if (!volatilitySurface || !volatilitySurface.expiries || volatilitySurface.expiries.length === 0) {
    return (
      <div className="loading">
        No volatility surface data available
      </div>
    );
  }

  const { expiries } = volatilitySurface;

  // Get all unique strikes across all expiries
  const allStrikes = [...new Set(expiries.flatMap(e => e.strikes || []))].sort((a, b) => a - b);

  // Create IV map
  const ivMap = {};
  expiries.forEach(exp => {
    ivMap[exp.expiry] = {};
    (exp.strikes || []).forEach((strike, idx) => {
      const callIV = exp.call_ivs?.[idx];
      const putIV = exp.put_ivs?.[idx];
      ivMap[exp.expiry][strike] = (callIV || putIV || exp.avg_iv) || 0;
    });
  });

  const getColor = (iv) => {
    if (iv === undefined || iv === null) return 'var(--bg-tertiary)';
    const normalizedIV = iv; // IV is already in decimal form (0.15 = 15%)
    if (normalizedIV > 0.3) return `rgba(255, 107, 107, ${Math.min(normalizedIV * 2, 1)})`;
    if (normalizedIV > 0.2) return `rgba(255, 217, 61, ${normalizedIV * 2})`;
    return `rgba(0, 214, 143, ${normalizedIV * 2 + 0.3})`;
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
        <thead>
          <tr>
            <th style={{ padding: '0.5rem', background: 'var(--bg-tertiary)', textAlign: 'left' }}>
              Strike \ Expiry
            </th>
            {expiries.map(exp => (
              <th
                key={exp.expiry}
                style={{
                  padding: '0.5rem',
                  background: 'var(--bg-tertiary)',
                  textAlign: 'center',
                  whiteSpace: 'nowrap',
                }}
              >
                {exp.expiry}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {allStrikes.slice(0, 15).map(strike => (
            <tr key={strike}>
              <td style={{ padding: '0.5rem', fontWeight: 600 }}>
                {strike.toLocaleString()}
              </td>
              {expiries.map(exp => {
                const iv = ivMap[exp.expiry]?.[strike];
                return (
                  <td
                    key={`${strike}-${exp.expiry}`}
                    style={{
                      padding: '0.5rem',
                      textAlign: 'center',
                      background: getColor(iv),
                      color: iv > 0.25 ? 'white' : 'inherit',
                    }}
                  >
                    {iv ? `${(iv * 100).toFixed(1)}%` : '-'}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', fontSize: '0.75rem' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ width: 16, height: 16, background: 'rgba(0, 214, 143, 0.5)', borderRadius: 4 }} />
          Low IV (&lt;20%)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ width: 16, height: 16, background: 'rgba(255, 217, 61, 0.5)', borderRadius: 4 }} />
          Medium IV (20-30%)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ width: 16, height: 16, background: 'rgba(255, 107, 107, 0.7)', borderRadius: 4 }} />
          High IV (&gt;30%)
        </span>
      </div>
    </div>
  );
}
