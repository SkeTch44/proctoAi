import os
import json
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import jwt
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from questions import QuestionGenerator
from grading import GradingEngine
from models.cheat_detector import CheatDetector
from utils.pdf_parser import parse_pdf
from utils.docx_parser import parse_docx
# from utils.report_export import generate_exam_report
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=app.config['CORS_ORIGINS'])
socketio = SocketIO(app, cors_allowed_origins=app.config['CORS_ORIGINS'])

# Initialize components
question_generator = QuestionGenerator()
grading_engine = GradingEngine()
cheat_detector = CheatDetector()

# Database setup
def init_db():
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Exams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            questions TEXT NOT NULL,
            duration INTEGER DEFAULT 3600,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            answers TEXT,
            score REAL DEFAULT 0,
            suspicion_score INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (exam_id) REFERENCES exams (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Proctoring events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proctoring_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# JWT token authentication
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            current_user_role = data['role']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user_id, current_user_role, *args, **kwargs)
    return decorated

# Authentication routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'student')
    
    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400
    
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    
    try:
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                      (username, password_hash, role))
        conn.commit()
        user_id = cursor.lastrowid
        
        token = jwt.encode({
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['JWT_SECRET_KEY'])
        
        return jsonify({'token': token, 'user': {'id': user_id, 'username': username, 'role': role}})
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Username already exists'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400
    
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password_hash, role FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        token = jwt.encode({
            'user_id': user[0],
            'username': user[1],
            'role': user[3],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['JWT_SECRET_KEY'])
        
        return jsonify({'token': token, 'user': {'id': user[0], 'username': user[1], 'role': user[3]}})
    
    return jsonify({'message': 'Invalid credentials'}), 401

# Document upload and processing
@app.route('/api/upload_document', methods=['POST'])
@token_required
def upload_document(user_id, user_role):
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    
    if 'file' not in request.files:
        return jsonify({'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()
    
    if file_ext == 'pdf':
        content = parse_pdf(file)
    elif file_ext == 'docx':
        content = parse_docx(file)
    else:
        return jsonify({'message': 'Unsupported file type'}), 400
    
    return jsonify({
        'message': 'Document uploaded successfully',
        'content_preview': content[:500],
        'content_length': len(content)
    })

# Question generation
@app.route('/api/generate_questions', methods=['POST'])
@token_required
def generate_questions_endpoint(user_id, user_role):
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    
    data = request.get_json()
    content = data.get('content', '')
    question_count = data.get('question_count', 10)
    difficulty = data.get('difficulty', 'medium')
    
    if not content:
        return jsonify({'message': 'Content is required'}), 400
    
    try:
        questions = question_generator.generate_questions(content, question_count, difficulty)
        return jsonify({'questions': questions})
    except Exception as e:
        return jsonify({'message': f'Question generation failed: {str(e)}'}), 500

# Exam management
@app.route('/api/exams', methods=['GET'])
@token_required
def get_exams(user_id, user_role):
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, description, duration FROM exams')
    exams = cursor.fetchall()
    conn.close()
    
    exam_list = []
    for exam in exams:
        exam_list.append({
            'id': exam[0],
            'title': exam[1],
            'description': exam[2],
            'duration': exam[3]
        })
    
    return jsonify({'exams': exam_list})

@app.route('/api/exams', methods=['POST'])
@token_required
def create_exam(user_id, user_role):
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    
    data = request.get_json()
    title = data.get('title')
    description = data.get('description', '')
    questions = data.get('questions', [])
    duration = data.get('duration', 3600)
    
    if not title or not questions:
        return jsonify({'message': 'Title and questions are required'}), 400
    
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO exams (title, description, questions, duration, created_by) VALUES (?, ?, ?, ?, ?)',
        (title, description, json.dumps(questions), duration, user_id)
    )
    conn.commit()
    exam_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'exam_id': exam_id, 'message': 'Exam created successfully'})

# Exam session management
@app.route('/api/start_exam', methods=['POST'])
@token_required
def start_exam(user_id, user_role):
    data = request.get_json()
    exam_id = data.get('exam_id')
    
    if not exam_id:
        return jsonify({'message': 'Exam ID is required'}), 400
    
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    
    # Get exam details
    cursor.execute('SELECT id, title, questions, duration FROM exams WHERE id = ?', (exam_id,))
    exam = cursor.fetchone()
    
    if not exam:
        return jsonify({'message': 'Exam not found'}), 404
    
    # Create session
    cursor.execute(
        'INSERT INTO sessions (exam_id, user_id, status) VALUES (?, ?, ?)',
        (exam_id, user_id, 'active')
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    questions = json.loads(exam[2])
    
    return jsonify({
        'session_id': session_id,
        'exam_title': exam[1],
        'questions': questions,
        'duration': exam[3]
    })

@app.route('/api/submit_answer', methods=['POST'])
@token_required
def submit_answer(user_id, user_role):
    data = request.get_json()
    session_id = data.get('session_id')
    question_id = data.get('question_id')
    answer = data.get('answer')
    
    if not all([session_id, question_id, answer]):
        return jsonify({'message': 'Session ID, question ID, and answer are required'}), 400
    
    # Store answer (simplified - in production, you'd update incrementally)
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    cursor.execute('SELECT answers FROM sessions WHERE id = ? AND user_id = ?', (session_id, user_id))
    result = cursor.fetchone()
    
    if not result:
        return jsonify({'message': 'Session not found'}), 404
    
    answers = json.loads(result[0] or '{}')
    answers[str(question_id)] = answer
    
    cursor.execute('UPDATE sessions SET answers = ? WHERE id = ?', (json.dumps(answers), session_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Answer submitted successfully'})

@app.route('/api/end_exam', methods=['POST'])
@token_required
def end_exam(user_id, user_role):
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'message': 'Session ID is required'}), 400
    
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    
    # Get session and exam data
    cursor.execute('''
        SELECT s.answers, e.questions 
        FROM sessions s 
        JOIN exams e ON s.exam_id = e.id 
        WHERE s.id = ? AND s.user_id = ?
    ''', (session_id, user_id))
    result = cursor.fetchone()
    
    if not result:
        return jsonify({'message': 'Session not found'}), 404
    
    answers = json.loads(result[0] or '{}')
    questions = json.loads(result[1])
    
    # Grade the exam
    score = grading_engine.grade_exam(questions, answers)
    
    # Update session
    cursor.execute('''
        UPDATE sessions 
        SET completed_at = CURRENT_TIMESTAMP, status = 'completed', score = ?
        WHERE id = ?
    ''', (score, session_id))
    conn.commit()
    conn.close()
    
    return jsonify({'score': score, 'message': 'Exam completed successfully'})

# Proctoring endpoints
@app.route('/api/proctoring_event', methods=['POST'])
@token_required
def log_proctoring_event(user_id, user_role):
    data = request.get_json()
    session_id = data.get('session_id')
    event_type = data.get('event_type')
    severity = data.get('severity', 'low')
    details = data.get('details', '')
    
    if not all([session_id, event_type]):
        return jsonify({'message': 'Session ID and event type are required'}), 400
    
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO proctoring_events (session_id, event_type, severity, details) VALUES (?, ?, ?, ?)',
        (session_id, event_type, severity, details)
    )
    conn.commit()
    
    # Update suspicion score
    suspicion_increase = {'low': 1, 'medium': 3, 'high': 5, 'critical': 10}.get(severity, 1)
    cursor.execute(
        'UPDATE sessions SET suspicion_score = suspicion_score + ? WHERE id = ?',
        (suspicion_increase, session_id)
    )
    conn.commit()
    conn.close()
    
    # Emit real-time alert to admins
    socketio.emit('proctoring_alert', {
        'session_id': session_id,
        'event_type': event_type,
        'severity': severity,
        'details': details,
        'timestamp': datetime.now().isoformat()
    }, room='admins')
    
    return jsonify({'message': 'Event logged successfully'})

# Admin dashboard endpoints
@app.route('/api/admin/dashboard', methods=['GET'])
@token_required
def admin_dashboard(user_id, user_role):
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    
    conn = sqlite3.connect('exam_platform.db')
    cursor = conn.cursor()
    
    # Get active sessions
    cursor.execute('''
        SELECT s.id, u.username, e.title, s.suspicion_score, s.started_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        JOIN exams e ON s.exam_id = e.id
        WHERE s.status = 'active'
    ''')
    active_sessions = cursor.fetchall()
    
    # Get recent alerts
    cursor.execute('''
        SELECT pe.event_type, pe.severity, pe.timestamp, u.username
        FROM proctoring_events pe
        JOIN sessions s ON pe.session_id = s.id
        JOIN users u ON s.user_id = u.id
        ORDER BY pe.timestamp DESC
        LIMIT 20
    ''')
    recent_alerts = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'active_sessions': [
            {
                'session_id': session[0],
                'username': session[1],
                'exam_title': session[2],
                'suspicion_score': session[3],
                'started_at': session[4]
            }
            for session in active_sessions
        ],
        'recent_alerts': [
            {
                'event_type': alert[0],
                'severity': alert[1],
                'timestamp': alert[2],
                'username': alert[3]
            }
            for alert in recent_alerts
        ]
    })

# WebSocket events
@socketio.on('join_admin')
def on_join_admin():
    join_room('admins')
    emit('status', {'message': 'Connected to admin dashboard'})

@socketio.on('join_session')
def on_join_session(data):
    session_id = data.get('session_id')
    if session_id:
        join_room(f'session_{session_id}')
        emit('status', {'message': f'Joined session {session_id}'})

@socketio.on('proctoring_data')
def handle_proctoring_data(data):
    # Process real-time proctoring data
    session_id = data.get('session_id')
    frame_data = data.get('frame_data')
    
    if session_id and frame_data:
        # Analyze frame for suspicious activity
        analysis_result = cheat_detector.analyze_frame(frame_data)
        
        if analysis_result.get('suspicious'):
            # Emit alert to admins
            socketio.emit('proctoring_alert', {
                'session_id': session_id,
                'alert_type': analysis_result.get('alert_type'),
                'confidence': analysis_result.get('confidence'),
                'timestamp': datetime.now().isoformat()
            }, room='admins')

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
