import { useEffect, useState, useCallback, useRef } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = process.env.REACT_APP_SOCKET_URL || 'http://localhost:8002';

export function useSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [prices, setPrices] = useState({});
  const [chainSummaries, setChainSummaries] = useState({});
  const [fullChains, setFullChains] = useState({});
  const [subscribedProducts, setSubscribedProducts] = useState([]);
  const socketRef = useRef(null);

  useEffect(() => {
    // Initialize socket connection
    const socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    // Connection handlers
    socket.on('connect', () => {
      console.log('Connected to Socket Gateway');
      setIsConnected(true);
      
      // Resubscribe to products after reconnection
      subscribedProducts.forEach(product => {
        socket.emit('subscribe', { type: 'product', symbol: product });
        socket.emit('subscribe', { type: 'chain', symbol: product });
      });
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from Socket Gateway');
      setIsConnected(false);
    });

    socket.on('connect_error', (error) => {
      console.error('Connection error:', error);
      setIsConnected(false);
    });

    // Data handlers
    socket.on('underlying_update', (data) => {
      setPrices(prev => ({
        ...prev,
        [data.product]: {
          price: data.price,
          timestamp: data.timestamp,
          prevPrice: prev[data.product]?.price || data.price,
        },
      }));
    });

    socket.on('chain_summary', (data) => {
      setChainSummaries(prev => ({
        ...prev,
        [data.product]: data,
      }));
    });

    socket.on('chain_update', (data) => {
      setFullChains(prev => ({
        ...prev,
        [data.product]: data,
      }));
    });

    socket.on('subscribed', (data) => {
      console.log('Subscribed to:', data.room);
    });

    // Cleanup
    return () => {
      socket.disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const subscribe = useCallback((product) => {
    if (socketRef.current && !subscribedProducts.includes(product)) {
      socketRef.current.emit('subscribe', { type: 'product', symbol: product });
      socketRef.current.emit('subscribe', { type: 'chain', symbol: product });
      setSubscribedProducts(prev => [...prev, product]);
    }
  }, [subscribedProducts]);

  const unsubscribe = useCallback((product) => {
    if (socketRef.current) {
      socketRef.current.emit('unsubscribe', { type: 'product', symbol: product });
      socketRef.current.emit('unsubscribe', { type: 'chain', symbol: product });
      setSubscribedProducts(prev => prev.filter(p => p !== product));
    }
  }, []);

  return {
    isConnected,
    prices,
    chainSummaries,
    fullChains,
    subscribe,
    unsubscribe,
    subscribedProducts,
  };
}
