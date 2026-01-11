import { io } from 'socket.io-client';
let socket = null;

export function getSocket() {
  if (socket) return socket;
  socket = io('http://localhost:5000', { transports: ['websocket', 'polling'] });
  return socket;
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}
