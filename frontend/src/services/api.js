import axios from 'axios';

// API Gateway URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// Data endpoints
export const getProducts = () => api.get('/api/data/products');
export const getUnderlying = (product, limit = 100) => 
  api.get(`/api/data/underlying/${product}?limit=${limit}`);
export const getOptionChain = (product, limit = 1) => 
  api.get(`/api/data/chain/${product}?limit=${limit}`);
export const getExpiries = (product) => api.get(`/api/data/expiries/${product}`);

// Analytics endpoints
export const getPCR = (product, history = false) => 
  api.get(`/api/analytics/pcr/${product}?history=${history}`);
export const getVolatilitySurface = (product) => 
  api.get(`/api/analytics/volatility-surface/${product}`);
export const getMaxPain = (product, expiry) => 
  api.get(`/api/analytics/max-pain/${product}?expiry=${expiry}`);
export const getOIBuildup = (product, expiry) => 
  api.get(`/api/analytics/oi-buildup/${product}?expiry=${expiry}`);
export const getOHLC = (product, window = 5) => 
  api.get(`/api/analytics/ohlc/${product}?window=${window}`);

// Auth endpoints
export const login = (email, password) => 
  api.post('/api/auth/login', { email, password });
export const register = (email, password, name) => 
  api.post('/api/auth/register', { email, password, name });
export const verifyToken = () => api.post('/api/auth/verify');

export default api;
