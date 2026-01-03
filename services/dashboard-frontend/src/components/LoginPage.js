import React, { useState } from 'react';
import { LogIn, UserPlus, Eye, EyeOff } from 'lucide-react';
import * as api from '../services/api';

export function LoginPage({ onLoginSuccess }) {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            let response;
            if (isLogin) {
                response = await api.login(email, password);
            } else {
                response = await api.register(name, email, password);
                // After register, login
                response = await api.login(email, password);
            }

            // Store token
            localStorage.setItem('token', response.data.token);
            localStorage.setItem('user', JSON.stringify(response.data.user));

            onLoginSuccess(response.data);
        } catch (err) {
            setError(err.response?.data?.error || 'Authentication failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            padding: '2rem',
        }}>
            <div style={{
                background: 'white',
                borderRadius: '12px',
                boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                padding: '3rem',
                width: '100%',
                maxWidth: '400px',
            }}>
                {/* Logo */}
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <h1 style={{
                        fontSize: '2rem',
                        fontWeight: 'bold',
                        background: 'linear-gradient(135deg, #667eea, #764ba2)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                    }}>
                        DeltaStream
                    </h1>
                    <p style={{ color: '#666', marginTop: '0.5rem' }}>
                        Real-time Options Analytics
                    </p>
                </div>

                {/* Tabs */}
                <div style={{
                    display: 'flex',
                    gap: '0.5rem',
                    marginBottom: '2rem',
                    borderBottom: '2px solid #e2e8f0',
                }}>
                    <button
                        onClick={() => setIsLogin(true)}
                        style={{
                            flex: 1,
                            padding: '0.75rem',
                            border: 'none',
                            background: 'none',
                            borderBottom: isLogin ? '3px solid #667eea' : 'none',
                            color: isLogin ? '#667eea' : '#666',
                            fontWeight: isLogin ? 'bold' : 'normal',
                            cursor: 'pointer',
                        }}
                    >
                        <LogIn size={18} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
                        Login
                    </button>
                    <button
                        onClick={() => setIsLogin(false)}
                        style={{
                            flex: 1,
                            padding: '0.75rem',
                            border: 'none',
                            background: 'none',
                            borderBottom: !isLogin ? '3px solid #667eea' : 'none',
                            color: !isLogin ? '#667eea' : '#666',
                            fontWeight: !isLogin ? 'bold' : 'normal',
                            cursor: 'pointer',
                        }}
                    >
                        <UserPlus size={18} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
                        Register
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit}>
                    {!isLogin && (
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#333', fontWeight: '500' }}>
                                Name
                            </label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required={!isLogin}
                                placeholder="John Doe"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '2px solid #e2e8f0',
                                    borderRadius: '8px',
                                    fontSize: '1rem',
                                }}
                            />
                        </div>
                    )}

                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#333', fontWeight: '500' }}>
                            Email
                        </label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            placeholder="you@example.com"
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '2px solid #e2e8f0',
                                borderRadius: '8px',
                                fontSize: '1rem',
                            }}
                        />
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#333', fontWeight: '500' }}>
                            Password
                        </label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                placeholder="••••••••"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    paddingRight: '3rem',
                                    border: '2px solid #e2e8f0',
                                    borderRadius: '8px',
                                    fontSize: '1rem',
                                }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                style={{
                                    position: 'absolute',
                                    right: '0.75rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    border: 'none',
                                    background: 'none',
                                    cursor: 'pointer',
                                    color: '#666',
                                }}
                            >
                                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                            </button>
                        </div>
                    </div>

                    {error && (
                        <div style={{
                            padding: '0.75rem',
                            background: '#fee2e2',
                            border: '1px solid #fecaca',
                            borderRadius: '8px',
                            color: '#dc2626',
                            marginBottom: '1.5rem',
                            fontSize: '0.875rem',
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: '100%',
                            padding: '0.875rem',
                            background: 'linear-gradient(135deg, #667eea, #764ba2)',
                            border: 'none',
                            borderRadius: '8px',
                            color: 'white',
                            fontSize: '1rem',
                            fontWeight: 'bold',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.7 : 1,
                        }}
                    >
                        {loading ? 'Please wait...' : (isLogin ? 'Login' : 'Create Account')}
                    </button>
                </form>

                {/* Demo credentials */}
                <div style={{
                    marginTop: '2rem',
                    padding: '1rem',
                    background: '#f8fafc',
                    borderRadius: '8px',
                    fontSize: '0.875rem',
                    color: '#64748b',
                }}>
                    <p style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>Demo Credentials:</p>
                    <p>Email: demo@deltastream.com</p>
                    <p>Password: demo123</p>
                </div>
            </div>
        </div>
    );
}
