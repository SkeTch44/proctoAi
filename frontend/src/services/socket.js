import { io } from 'socket.io-client';

let socket = null;
let connectionListeners = [];

export function getSocket() {
  if (socket) return socket;

  socket = io('http://127.0.0.1:5000', {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 20000,
    autoConnect: true
  });

  // Connection event handlers
  socket.on('connect', () => {
    console.log('[Socket] Connected to server', socket.id);
    notifyConnectionListeners('connected', socket.id);
  });

  socket.on('disconnect', (reason) => {
    console.warn('[Socket] Disconnected:', reason);
    notifyConnectionListeners('disconnected', reason);
  });

  socket.on('connect_error', (error) => {
    console.error('[Socket] Connection error:', error.message);
    notifyConnectionListeners('error', error.message);
  });

  socket.on('reconnect', (attemptNumber) => {
    console.log('[Socket] Reconnected after', attemptNumber, 'attempts');
    notifyConnectionListeners('reconnected', attemptNumber);
  });

  socket.on('reconnect_attempt', (attemptNumber) => {
    console.log('[Socket] Reconnection attempt', attemptNumber);
    notifyConnectionListeners('reconnecting', attemptNumber);
  });

  socket.on('reconnect_failed', () => {
    console.error('[Socket] Reconnection failed after all attempts');
    notifyConnectionListeners('reconnect_failed', null);
  });

  return socket;
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
    connectionListeners = [];
  }
}

export function onConnectionChange(callback) {
  connectionListeners.push(callback);
  return () => {
    connectionListeners = connectionListeners.filter(cb => cb !== callback);
  };
}

function notifyConnectionListeners(status, data) {
  connectionListeners.forEach(callback => {
    try {
      callback(status, data);
    } catch (err) {
      console.error('[Socket] Error in connection listener:', err);
    }
  });
}

export function isConnected() {
  return socket?.connected || false;
}
