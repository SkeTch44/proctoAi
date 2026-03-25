"""
Minimal Socket.IO Test Server
Tests the socket stabilization implementation without full app dependencies
"""
from flask import Flask
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app, origins='*')  # Allow all origins for testing

# Socket.IO with our stabilization config
socketio = SocketIO(
    app, 
    cors_allowed_origins='*',  # Allow all origins for testing
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

@app.route('/health')
def health():
    return {'status': 'ok', 'timestamp': datetime.utcnow().isoformat() + 'Z'}

@socketio.on('connect')
def handle_connect():
    print(f'[Server] Client connected: {request.sid}')
    emit('status', {'message': 'Connected to test server'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'[Server] Client disconnected: {request.sid}')

@socketio.on('join_session')
def on_join_session(data):
    session_id = data.get('session_id')
    if session_id:
        room = f'session_{session_id}'
        join_room(room)
        print(f'[Server] Client joined room: {room}')
        emit('status', {'message': f'Joined session {session_id}'})

@socketio.on('test_alert')
def on_test_alert(data):
    """Test proctoring alert emission"""
    session_id = data.get('session_id', 1)
    socketio.emit('proctoring_alert', {
        'session_id': session_id,
        'event_type': 'test_event',
        'severity': 'low',
        'details': 'This is a test alert',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'server_time': datetime.utcnow().timestamp()
    }, room='admins')
    print(f'[Server] Test alert sent for session {session_id}')

if __name__ == '__main__':
    print('='*60)
    print('Socket.IO Test Server')
    print('='*60)
    print('Server running on: http://localhost:5000')
    print('Socket endpoint: ws://localhost:5000/socket.io/')
    print('CORS allowed: http://localhost:3000')
    print('='*60)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
