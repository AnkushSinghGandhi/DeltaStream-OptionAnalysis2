import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Activity, ShoppingCart, X } from 'lucide-react';
import * as api from '../services/api';

export function Trading() {
    const [portfolio, setPortfolio] = useState(null);
    const [positions, setPositions] = useState([]);
    const [orders, setOrders] = useState([]);
    const [orderForm, setOrderForm] = useState({
        symbol: '',
        orderType: 'MARKET',
        side: 'BUY',
        quantity: 50,
        price: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchPortfolio();
        fetchPositions();
        fetchOrders();
    }, []);

    const fetchPortfolio = async () => {
        try {
            const response = await api.getPortfolio();
            setPortfolio(response.data);
        } catch (err) {
            console.error('Failed to fetch portfolio:', err);
        }
    };

    const fetchPositions = async () => {
        try {
            const response = await api.getPositions();
            setPositions(response.data.positions || []);
        } catch (err) {
            console.error('Failed to fetch positions:', err);
        }
    };

    const fetchOrders = async () => {
        try {
            const response = await api.getOrders();
            setOrders(response.data.orders || []);
        } catch (err) {
            console.error('Failed to fetch orders:', err);
        }
    };

    const handlePlaceOrder = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            await api.placeOrder(orderForm);

            // Refresh data
            await Promise.all([fetchPortfolio(), fetchPositions(), fetchOrders()]);

            // Reset form
            setOrderForm({ ...orderForm, symbol: '', price: '' });
            alert('Order placed successfully!');
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to place order');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '2rem' }}>
            <h2 style={{ marginBottom: '2rem', fontSize: '1.5rem', fontWeight: 'bold' }}>
                Paper Trading
            </h2>

            {/* Portfolio Summary */}
            <div className="dashboard-grid" style={{ marginBottom: '2rem' }}>
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">
                            <DollarSign size={18} />
                            Cash Balance
                        </span>
                    </div>
                    <div className="card-value" style={{ color: 'var(--accent-green)' }}>
                        ₹{portfolio?.cash_balance?.toLocaleString() || '0'}
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <span className="card-title">
                            <Activity size={18} />
                            Total P&L
                        </span>
                    </div>
                    <div
                        className="card-value"
                        style={{ color: (portfolio?.total_pnl || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}
                    >
                        {(portfolio?.total_pnl || 0) >= 0 ? '+' : ''}₹{portfolio?.total_pnl?.toLocaleString() || '0'}
                    </div>
                    <div className="card-subtitle">
                        Realized: ₹{portfolio?.realized_pnl?.toFixed(2) || '0'} |
                        Unrealized: ₹{portfolio?.unrealized_pnl?.toFixed(2) || '0'}
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Margin Used</span>
                    </div>
                    <div className="card-value">
                        ₹{portfolio?.margin_used?.toLocaleString() || '0'}
                    </div>
                    <div className="card-subtitle">
                        Available: ₹{portfolio?.margin_available?.toLocaleString() || '0'}
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Open Positions</span>
                    </div>
                    <div className="card-value" style={{ color: 'var(--accent-blue)' }}>
                        {positions.length}
                    </div>
                </div>
            </div>

            {/* Order Form */}
            <div className="card card-full" style={{ marginBottom: '2rem' }}>
                <div className="card-header">
                    <span className="card-title">
                        <ShoppingCart size={18} />
                        Place Order
                    </span>
                </div>
                <form onSubmit={handlePlaceOrder} style={{ padding: '1rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                Symbol
                            </label>
                            <input
                                type="text"
                                value={orderForm.symbol}
                                onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value.toUpperCase() })}
                                placeholder="NIFTY25JAN21500CE"
                                required
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '6px',
                                    background: 'var(--bg-secondary)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                Order Type
                            </label>
                            <select
                                value={orderForm.orderType}
                                onChange={(e) => setOrderForm({ ...orderForm, orderType: e.target.value })}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '6px',
                                    background: 'var(--bg-secondary)',
                                    color: 'var(--text-primary)',
                                }}
                            >
                                <option value="MARKET">Market</option>
                                <option value="LIMIT">Limit</option>
                            </select>
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                Side
                            </label>
                            <select
                                value={orderForm.side}
                                onChange={(e) => setOrderForm({ ...orderForm, side: e.target.value })}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '6px',
                                    background: 'var(--bg-secondary)',
                                    color: 'var(--text-primary)',
                                }}
                            >
                                <option value="BUY">Buy</option>
                                <option value="SELL">Sell</option>
                            </select>
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                Quantity
                            </label>
                            <input
                                type="number"
                                value={orderForm.quantity}
                                onChange={(e) => setOrderForm({ ...orderForm, quantity: parseInt(e.target.value) })}
                                min="1"
                                required
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '6px',
                                    background: 'var(--bg-secondary)',
                                    color: 'var(--text-primary)',
                                }}
                            />
                        </div>

                        {orderForm.orderType === 'LIMIT' && (
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                    Price
                                </label>
                                <input
                                    type="number"
                                    value={orderForm.price}
                                    onChange={(e) => setOrderForm({ ...orderForm, price: parseFloat(e.target.value) })}
                                    step="0.05"
                                    required={orderForm.orderType === 'LIMIT'}
                                    style={{
                                        width: '100%',
                                        padding: '0.75rem',
                                        border: '1px solid var(--border-color)',
                                        borderRadius: '6px',
                                        background: 'var(--bg-secondary)',
                                        color: 'var(--text-primary)',
                                    }}
                                />
                            </div>
                        )}
                    </div>

                    {error && (
                        <div style={{
                            marginTop: '1rem',
                            padding: '0.75rem',
                            background: 'var(--bg-error)',
                            border: '1px solid var(--border-error)',
                            borderRadius: '6px',
                            color: 'var(--accent-red)',
                            fontSize: '0.875rem',
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            marginTop: '1rem',
                            padding: '0.875rem 2rem',
                            background: orderForm.side === 'BUY' ? 'var(--accent-green)' : 'var(--accent-red)',
                            border: 'none',
                            borderRadius: '6px',
                            color: 'white',
                            fontWeight: 'bold',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.7 : 1,
                        }}
                    >
                        {loading ? 'Placing...' : `${orderForm.side} ${orderForm.quantity} ${orderForm.orderType === 'MARKET' ? '@ Market' : `@ ₹${orderForm.price}`}`}
                    </button>
                </form>
            </div>

            {/* Positions */}
            <div className="card card-full" style={{ marginBottom: '2rem' }}>
                <div className="card-header">
                    <span className="card-title">Open Positions</span>
                </div>
                {positions.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: '0.875rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <th style={{ padding: '0.75rem', textAlign: 'left' }}>Symbol</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>Qty</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>Avg Price</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>Current Price</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>P&L</th>
                                </tr>
                            </thead>
                            <tbody>
                                {positions.map((pos, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                        <td style={{ padding: '0.75rem' }}>{pos.symbol}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right', color: pos.quantity > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                            {pos.quantity > 0 ? '+' : ''}{pos.quantity}
                                        </td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>₹{pos.avg_entry_price?.toFixed(2)}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>₹{pos.current_price?.toFixed(2)}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right', color: pos.unrealized_pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                            {pos.unrealized_pnl >= 0 ? '+' : ''}₹{pos.unrealized_pnl?.toFixed(2)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No open positions
                    </div>
                )}
            </div>

            {/* Recent Orders */}
            <div className="card card-full">
                <div className="card-header">
                    <span className="card-title">Recent Orders</span>
                </div>
                {orders.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: '0.875rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <th style={{ padding: '0.75rem', textAlign: 'left' }}>Time</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left' }}>Symbol</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left' }}>Side</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>Qty</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>Price</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left' }}>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {orders.slice(0, 10).map((order, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                        <td style={{ padding: '0.75rem' }}>{new Date(order.placed_at).toLocaleTimeString()}</td>
                                        <td style={{ padding: '0.75rem' }}>{order.symbol}</td>
                                        <td style={{ padding: '0.75rem', color: order.side === 'BUY' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                            {order.side}
                                        </td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>{order.quantity}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                                            {order.avg_fill_price ? `₹${order.avg_fill_price.toFixed(2)}` : '-'}
                                        </td>
                                        <td style={{ padding: '0.75rem' }}>
                                            <span style={{
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: '4px',
                                                fontSize: '0.75rem',
                                                background: order.status === 'FILLED' ? 'var(--bg-success)' :
                                                    order.status === 'REJECTED' ? 'var(--bg-error)' : 'var(--bg-warning)',
                                                color: order.status === 'FILLED' ? 'var(--accent-green)' :
                                                    order.status === 'REJECTED' ? 'var(--accent-red)' : 'var(--accent-yellow)',
                                            }}>
                                                {order.status}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No orders yet
                    </div>
                )}
            </div>
        </div>
    );
}
