import React from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ComposedChart
} from 'recharts';

// Custom tooltip style
const tooltipStyle = {
  backgroundColor: '#1a1a2e',
  border: '1px solid #2d2d44',
  borderRadius: '8px',
  padding: '10px',
};

// Price Line Chart
export function PriceChart({ data, dataKey = 'price', color = '#4dabf7' }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data}>
        <defs>
          <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d2d44" />
        <XAxis 
          dataKey="time" 
          stroke="#6b6b80" 
          fontSize={12}
          tickFormatter={(value) => value ? value.split('T')[1]?.slice(0, 8) : ''}
        />
        <YAxis 
          stroke="#6b6b80" 
          fontSize={12}
          domain={['auto', 'auto']}
          tickFormatter={(value) => value.toLocaleString()}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Area 
          type="monotone" 
          dataKey={dataKey} 
          stroke={color} 
          fill="url(#priceGradient)" 
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// PCR Chart
export function PCRChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d2d44" />
        <XAxis 
          dataKey="time" 
          stroke="#6b6b80" 
          fontSize={12}
          tickFormatter={(value) => value ? value.split('T')[1]?.slice(0, 8) : ''}
        />
        <YAxis 
          yAxisId="left" 
          stroke="#6b6b80" 
          fontSize={12}
          domain={[0, 2]}
        />
        <YAxis 
          yAxisId="right" 
          orientation="right" 
          stroke="#6b6b80" 
          fontSize={12}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend />
        <Line 
          yAxisId="left"
          type="monotone" 
          dataKey="pcr_oi" 
          stroke="#9775fa" 
          strokeWidth={2}
          name="PCR (OI)"
          dot={false}
        />
        <Line 
          yAxisId="left"
          type="monotone" 
          dataKey="pcr_volume" 
          stroke="#ffd93d" 
          strokeWidth={2}
          name="PCR (Vol)"
          dot={false}
        />
        <Area 
          yAxisId="right"
          type="monotone" 
          dataKey="spot_price" 
          stroke="#4dabf7" 
          fill="rgba(77, 171, 247, 0.1)" 
          name="Spot"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// OI Distribution Bar Chart
export function OIChart({ calls, puts }) {
  // Prepare data for the chart
  const chartData = calls.map((call, index) => ({
    strike: call.strike,
    callOI: call.open_interest,
    putOI: puts[index]?.open_interest || 0,
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#2d2d44" />
        <XAxis type="number" stroke="#6b6b80" fontSize={12} />
        <YAxis 
          dataKey="strike" 
          type="category" 
          stroke="#6b6b80" 
          fontSize={11}
          width={60}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend />
        <Bar dataKey="callOI" fill="#00d68f" name="Call OI" />
        <Bar dataKey="putOI" fill="#ff6b6b" name="Put OI" />
      </BarChart>
    </ResponsiveContainer>
  );
}

// IV Smile Chart
export function IVSmileChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d2d44" />
        <XAxis 
          dataKey="strike" 
          stroke="#6b6b80" 
          fontSize={12}
        />
        <YAxis 
          stroke="#6b6b80" 
          fontSize={12}
          tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
        />
        <Tooltip 
          contentStyle={tooltipStyle}
          formatter={(value) => [`${(value * 100).toFixed(2)}%`, 'IV']}
        />
        <Legend />
        <Line 
          type="monotone" 
          dataKey="call_iv" 
          stroke="#00d68f" 
          strokeWidth={2}
          name="Call IV"
          dot={{ fill: '#00d68f', r: 3 }}
        />
        <Line 
          type="monotone" 
          dataKey="put_iv" 
          stroke="#ff6b6b" 
          strokeWidth={2}
          name="Put IV"
          dot={{ fill: '#ff6b6b', r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// OHLC / Candlestick-like Chart
export function OHLCChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d2d44" />
        <XAxis 
          dataKey="time" 
          stroke="#6b6b80" 
          fontSize={12}
        />
        <YAxis 
          stroke="#6b6b80" 
          fontSize={12}
          domain={['auto', 'auto']}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend />
        <Area 
          type="monotone" 
          dataKey="high" 
          stroke="#00d68f" 
          fill="rgba(0, 214, 143, 0.1)" 
          name="High"
        />
        <Area 
          type="monotone" 
          dataKey="low" 
          stroke="#ff6b6b" 
          fill="rgba(255, 107, 107, 0.1)" 
          name="Low"
        />
        <Line 
          type="monotone" 
          dataKey="close" 
          stroke="#4dabf7" 
          strokeWidth={2}
          name="Close"
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// Straddle Price Chart
export function StraddleChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data}>
        <defs>
          <linearGradient id="straddleGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#9775fa" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#9775fa" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d2d44" />
        <XAxis 
          dataKey="time" 
          stroke="#6b6b80" 
          fontSize={12}
          tickFormatter={(value) => value ? value.split('T')[1]?.slice(0, 8) : ''}
        />
        <YAxis 
          stroke="#6b6b80" 
          fontSize={12}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Area 
          type="monotone" 
          dataKey="straddle" 
          stroke="#9775fa" 
          fill="url(#straddleGradient)" 
          strokeWidth={2}
          name="ATM Straddle"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Max Pain Chart
export function MaxPainChart({ calls, puts, strikes, maxPain, spotPrice }) {
  const chartData = strikes.map((strike, index) => {
    const callPain = calls.reduce((sum, c) => 
      sum + c.open_interest * Math.max(0, strike - c.strike), 0);
    const putPain = puts.reduce((sum, p) => 
      sum + p.open_interest * Math.max(0, p.strike - strike), 0);
    
    return {
      strike,
      totalPain: callPain + putPain,
      isMaxPain: strike === maxPain,
      isSpot: Math.abs(strike - spotPrice) < (strikes[1] - strikes[0]) / 2,
    };
  });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2d2d44" />
        <XAxis 
          dataKey="strike" 
          stroke="#6b6b80" 
          fontSize={12}
        />
        <YAxis 
          stroke="#6b6b80" 
          fontSize={12}
          tickFormatter={(value) => `${(value / 1000000).toFixed(1)}M`}
        />
        <Tooltip 
          contentStyle={tooltipStyle}
          formatter={(value) => [value.toLocaleString(), 'Total Pain']}
        />
        <Bar 
          dataKey="totalPain" 
          fill="#4dabf7"
          name="Total Pain"
        >
          {chartData.map((entry, index) => (
            <rect 
              key={index}
              fill={entry.isMaxPain ? '#00d68f' : entry.isSpot ? '#ffd93d' : '#4dabf7'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
