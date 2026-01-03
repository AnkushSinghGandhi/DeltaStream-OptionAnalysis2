import React, { useState, useEffect } from 'react';
import { Brain, TrendingUp, MessageCircle, Sparkles, RefreshCw } from 'lucide-react';
import * as api from '../services/api';

export function AIInsights({ selectedProduct }) {
    const [pulse, setPulse] = useState(null);
    const [sentiment, setSentiment] = useState(null);
    const [chatHistory, setChatHistory] = useState([]);
    const [chatInput, setChatInput] = useState('');
    const [loading, setLoading] = useState({ pulse: false, sentiment: false, chat: false });

    useEffect(() => {
        fetchPulse();
        fetchSentiment();
    }, [selectedProduct]);

    const fetchPulse = async () => {
        try {
            setLoading(prev => ({ ...prev, pulse: true }));
            const response = await api.getMarketPulse(selectedProduct);
            setPulse(response.data);
        } catch (err) {
            console.error('Failed to fetch pulse:', err);
            setPulse({ error: 'Failed to load Market Pulse' });
        } finally {
            setLoading(prev => ({ ...prev, pulse: false }));
        }
    };

    const fetchSentiment = async () => {
        try {
            setLoading(prev => ({ ...prev, sentiment: true }));
            const response = await api.getSentiment();
            setSentiment(response.data);
        } catch (err) {
            console.error('Failed to fetch sentiment:', err);
            setSentiment({ error: 'Failed to load Sentiment' });
        } finally {
            setLoading(prev => ({ ...prev, sentiment: false }));
        }
    };

    const handleChat = async (e) => {
        e.preventDefault();
        if (!chatInput.trim()) return;

        const userMessage = chatInput;
        setChatHistory(prev => [...prev, { role: 'user', text: userMessage }]);
        setChatInput('');
        setLoading(prev => ({ ...prev, chat: true }));

        try {
            const response = await api.chatWithAI(userMessage);
            setChatHistory(prev => [...prev, {
                role: 'assistant',
                text: response.data.answer,
                sources: response.data.sources
            }]);
        } catch (err) {
            console.error('Chat error:', err);
            setChatHistory(prev => [...prev, {
                role: 'assistant',
                text: 'Sorry, I encountered an error. Please try again.'
            }]);
        } finally {
            setLoading(prev => ({ ...prev, chat: false }));
        }
    };

    const getSentimentColor = (sentiment) => {
        if (sentiment === 'Bullish') return 'var(--accent-green)';
        if (sentiment === 'Bearish') return 'var(--accent-red)';
        return 'var(--accent-yellow)';
    };

    return (
        <div>
            {/* Market Pulse Card */}
            <div className="card card-full">
                <div className="card-header">
                    <span className="card-title">
                        <Brain size={18} />
                        AI Market Pulse - {selectedProduct}
                    </span>
                    <button
                        onClick={fetchPulse}
                        disabled={loading.pulse}
                        style={{
                            background: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '6px',
                            padding: '0.5rem',
                            cursor: loading.pulse ? 'not-allowed' : 'pointer',
                            color: 'var(--text-secondary)',
                        }}
                    >
                        <RefreshCw size={16} className={loading.pulse ? 'spinning' : ''} />
                    </button>
                </div>
                {loading.pulse ? (
                    <div className="loading">
                        <div className="loading-spinner" />
                        <span style={{ marginLeft: '1rem' }}>Generating AI analysis...</span>
                    </div>
                ) : pulse?.error ? (
                    <div style={{ padding: '1rem', color: 'var(--accent-red)' }}>
                        {pulse.error}
                    </div>
                ) : pulse ? (
                    <div style={{ padding: '1.5rem' }}>
                        <div style={{
                            fontSize: '1rem',
                            lineHeight: '1.6',
                            color: 'var(--text-primary)',
                            whiteSpace: 'pre-wrap'
                        }}>
                            {pulse.analysis}
                        </div>
                        {pulse.data && (
                            <div style={{
                                marginTop: '1.5rem',
                                padding: '1rem',
                                background: 'var(--bg-tertiary)',
                                borderRadius: '8px',
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                                gap: '1rem'
                            }}>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PCR (OI)</div>
                                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--accent-blue)' }}>
                                        {pulse.data.pcr_oi?.toFixed(4) || '-'}
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Max Pain</div>
                                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--accent-purple)' }}>
                                        {pulse.data.max_pain_strike?.toLocaleString() || '-'}
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ATM Straddle</div>
                                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--accent-yellow)' }}>
                                        ₹{pulse.data.atm_straddle_price?.toFixed(2) || '-'}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="loading">Waiting for AI analysis...</div>
                )}
            </div>

            {/* Sentiment Analysis Card */}
            <div className="card card-full" style={{ marginTop: '1.5rem' }}>
                <div className="card-header">
                    <span className="card-title">
                        <TrendingUp size={18} />
                        News Sentiment Analysis
                    </span>
                    <button
                        onClick={fetchSentiment}
                        disabled={loading.sentiment}
                        style={{
                            background: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '6px',
                            padding: '0.5rem',
                            cursor: loading.sentiment ? 'not-allowed' : 'pointer',
                            color: 'var(--text-secondary)',
                        }}
                    >
                        <RefreshCw size={16} className={loading.sentiment ? 'spinning' : ''} />
                    </button>
                </div>
                {loading.sentiment ? (
                    <div className="loading">
                        <div className="loading-spinner" />
                        <span style={{ marginLeft: '1rem' }}>Analyzing news sentiment...</span>
                    </div>
                ) : sentiment?.error ? (
                    <div style={{ padding: '1rem', color: 'var(--accent-red)' }}>
                        {sentiment.error}
                    </div>
                ) : sentiment ? (
                    <div style={{ padding: '1.5rem' }}>
                        <div style={{
                            fontSize: '2.5rem',
                            fontWeight: 'bold',
                            color: getSentimentColor(sentiment.sentiment),
                            marginBottom: '1rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}>
                            <Sparkles size={32} />
                            {sentiment.sentiment || 'Neutral'}
                        </div>
                        <div style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                            Based on recent market news and analysis
                        </div>
                        {sentiment.headlines && sentiment.headlines.length > 0 && (
                            <div>
                                <h4 style={{ marginBottom: '1rem', fontSize: '1rem', fontWeight: 'bold' }}>
                                    Recent Headlines:
                                </h4>
                                <ul style={{ listStyle: 'none', padding: 0 }}>
                                    {sentiment.headlines.slice(0, 5).map((headline, idx) => (
                                        <li
                                            key={idx}
                                            style={{
                                                marginBottom: '0.75rem',
                                                padding: '0.75rem',
                                                background: 'var(--bg-tertiary)',
                                                borderRadius: '6px',
                                                borderLeft: '3px solid var(--accent-blue)'
                                            }}
                                        >
                                            {headline}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="loading">Waiting for sentiment data...</div>
                )}
            </div>

            {/* AI Chatbot */}
            <div className="card card-full" style={{ marginTop: '1.5rem' }}>
                <div className="card-header">
                    <span className="card-title">
                        <MessageCircle size={18} />
                        AI Options Assistant
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Powered by RAG
                    </span>
                </div>
                <div style={{ padding: '1rem' }}>
                    {/* Chat messages */}
                    <div style={{
                        maxHeight: '400px',
                        overflowY: 'auto',
                        marginBottom: '1rem',
                        padding: '0.5rem',
                        background: 'var(--bg-secondary)',
                        borderRadius: '8px'
                    }}>
                        {chatHistory.length === 0 ? (
                            <div style={{
                                padding: '2rem',
                                textAlign: 'center',
                                color: 'var(--text-muted)'
                            }}>
                                <MessageCircle size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
                                <p>Ask me anything about options trading!</p>
                                <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                                    Try: "What is Put-Call Ratio?" or "Explain delta hedging"
                                </p>
                            </div>
                        ) : (
                            chatHistory.map((msg, idx) => (
                                <div
                                    key={idx}
                                    style={{
                                        marginBottom: '1rem',
                                        display: 'flex',
                                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                                    }}
                                >
                                    <div style={{
                                        maxWidth: '80%',
                                        padding: '0.875rem',
                                        borderRadius: '12px',
                                        background: msg.role === 'user'
                                            ? 'var(--accent-blue)'
                                            : 'var(--bg-tertiary)',
                                        color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
                                        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                    }}>
                                        <div style={{
                                            fontSize: '0.75rem',
                                            fontWeight: 'bold',
                                            marginBottom: '0.5rem',
                                            opacity: 0.8
                                        }}>
                                            {msg.role === 'user' ? 'You' : 'AI Assistant'}
                                        </div>
                                        <div style={{ fontSize: '0.875rem', lineHeight: '1.5' }}>
                                            {msg.text}
                                        </div>
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div style={{
                                                marginTop: '0.75rem',
                                                fontSize: '0.75rem',
                                                opacity: 0.7,
                                                borderTop: '1px solid rgba(255,255,255,0.1)',
                                                paddingTop: '0.5rem'
                                            }}>
                                                Sources: {msg.sources.join(', ')}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                        {loading.chat && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}>
                                <div className="loading-spinner" style={{ width: '16px', height: '16px' }} />
                                <span>AI is thinking...</span>
                            </div>
                        )}
                    </div>

                    {/* Chat input */}
                    <form onSubmit={handleChat} style={{ display: 'flex', gap: '0.5rem' }}>
                        <input
                            type="text"
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            placeholder="Ask about options, strategies, greeks, risk management..."
                            disabled={loading.chat}
                            style={{
                                flex: 1,
                                padding: '0.875rem',
                                border: '2px solid var(--border-color)',
                                borderRadius: '8px',
                                background: 'var(--bg-secondary)',
                                color: 'var(--text-primary)',
                                fontSize: '0.875rem'
                            }}
                        />
                        <button
                            type="submit"
                            disabled={loading.chat || !chatInput.trim()}
                            style={{
                                padding: '0.875rem 1.5rem',
                                background: loading.chat || !chatInput.trim()
                                    ? 'var(--bg-tertiary)'
                                    : 'var(--accent-blue)',
                                border: 'none',
                                borderRadius: '8px',
                                color: 'white',
                                fontWeight: 'bold',
                                cursor: loading.chat || !chatInput.trim() ? 'not-allowed' : 'pointer',
                                opacity: loading.chat || !chatInput.trim() ? 0.5 : 1,
                                transition: 'all 0.2s'
                            }}
                        >
                            {loading.chat ? '...' : 'Send'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
