/**
 * WebSocket Client Example (Node.js)
 * 
 * Demonstrates connecting to Socket Gateway and subscribing to market data.
 * 
 * Install: npm install socket.io-client
 * Run: node subscribe-example.js
 */

const io = require('socket.io-client');

const SOCKET_URL = process.env.SOCKET_URL || 'http://localhost:8002';
const PRODUCT = process.env.PRODUCT || 'NIFTY';

console.log(`Connecting to ${SOCKET_URL}...`);
const socket = io(SOCKET_URL);

// Handle connection
socket.on('connect', () => {
    console.log('Connected to Socket Gateway');
    console.log(`Client ID: ${socket.id}`);
    
    // Subscribe to product updates
    console.log(`Subscribing to ${PRODUCT} updates...`);
    socket.emit('subscribe', {type: 'product', symbol: PRODUCT});
    socket.emit('subscribe', {type: 'chain', symbol: PRODUCT});
    
    // Get products list
    socket.emit('get_products');
});

// Handle connection confirmation
socket.on('connected', (data) => {
    console.log('Connection confirmed:', data);
});

// Handle subscription confirmation
socket.on('subscribed', (data) => {
    console.log('Subscribed:', data.room);
});

// Handle products list
socket.on('products', (data) => {
    console.log('Available products:', data.products);
});

// Handle underlying price updates
socket.on('underlying_update', (data) => {
    console.log(`[${new Date().toISOString()}] ${data.product} Price: ${data.price}`);
});

// Handle chain summaries
socket.on('chain_summary', (data) => {
    console.log(`\n[Chain Summary] ${data.product} (${data.expiry})`);
    console.log(`  Spot: ${data.spot_price}`);
    console.log(`  PCR (OI): ${data.pcr_oi}`);
    console.log(`  PCR (Vol): ${data.pcr_volume}`);
    console.log(`  ATM Straddle: ${data.atm_straddle_price}`);
});

// Handle full chain updates
socket.on('chain_update', (data) => {
    console.log(`\n[Full Chain] ${data.product} (${data.expiry})`);
    console.log(`  Strikes: ${data.strikes.length}`);
    console.log(`  Max Pain: ${data.max_pain_strike}`);
    console.log(`  Total Call OI: ${data.total_call_oi}`);
    console.log(`  Total Put OI: ${data.total_put_oi}`);
});

// Handle disconnection
socket.on('disconnect', () => {
    console.log('Disconnected from Socket Gateway');
});

// Handle errors
socket.on('error', (error) => {
    console.error('Error:', error);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\nShutting down...');
    socket.disconnect();
    process.exit(0);
});
