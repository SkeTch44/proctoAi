# Proper package execution recommended: python -m backend.app
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
import traceback
import logging
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import jwt
import io
from flask import Flask, request, jsonify, send_file, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flasgger import Swagger
from backend.utils.auth import token_required

from backend.questions import QuestionGenerator
from backend.grading import GradingEngine

from backend.utils.pdf_parser import parse_pdf
from backend.utils.docx_parser import parse_docx
from backend.utils.report_export import generate_exam_report
from backend.utils.question_sanitizer import sanitize_questions, sanitize_question
from backend.config import Config
from backend.db.database import DatabaseManager

# Lazy Loader Providers
from backend.providers.llm_provider import get_llm_client
from backend.providers.rag_provider import get_rag_engine
from backend.providers.cheat_detector_provider import get_cheat_detector
from backend.providers.question_gen_provider import get_question_generator
from backend.providers.grading_provider import get_grading_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB limit
# Initialize Flasgger
swagger = Swagger(app)

CORS(app, origins=app.config.get('CORS_ORIGINS', ['http://localhost:3000']))

# Rate limiter (in-memory for dev; use Redis storage_uri in production)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Point 7: Redis connectivity check
broker_url = app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
redis_available = False
try:
    import redis
    if 'redis://' in broker_url:
        r = redis.from_url(broker_url, socket_timeout=1.0, socket_connect_timeout=1.0)
        r.ping()
        redis_available = True
        logger.info(f"Connected to Redis broker at {broker_url}")
except Exception as e:
    logger.warning(f"Could not connect to Redis broker: {e}. Celery/SocketIO tasks may fail.")

socketio = SocketIO(
    app, 
    cors_allowed_origins=app.config.get('CORS_ORIGINS', ['http://localhost:3000']),
    async_mode='gevent',
    message_queue=None,  # Temporarily disabled to debug 401
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Global state for real-time exam management
# Format: {exam_id: {'title': str, 'students': {student_session_id: {'name': str, 'joined_at': str}}}}
waiting_room_cache = {}
# Format: {exam_id} - set of IDs for exams that have been 'unlocked' by admin
active_exams_cache = set()

# Redis check moved before SocketIO initialization
logger.info(f"CORS_ORIGINS: {app.config.get('CORS_ORIGINS')}")
logger.info(f"Redis Available: {redis_available}")

# Initial components (Lightweight ones remain, heavy ones moved to providers)
# question_generator, grading_engine, cheat_detector are now lazy-loaded via get_* functions

from backend.question_bank import QuestionBankManager, Question # Import Question models

_db_url = os.getenv("DATABASE_URL", "sqlite:///exam_platform.db")
db_manager = DatabaseManager(_db_url)
qb_manager = QuestionBankManager(_db_url)

from backend.celery_app import celery

# Coding-room routes
from backend.coding.routes import coding_bp
app.register_blueprint(coding_bp)

# Production Strategy: is_gunicorn_worker() check
def is_gunicorn_worker():
    """Detect if we are running inside a Gunicorn worker process."""
    return "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")

def preload_heavy_components():
    """
    Cold Start Strategy: Preload CRITICAL components in background.
    Non-critical components (YOLO, TF) remain fully lazy.
    """
    logger.info("[App] Background preloading critical components (LLM, RAG)...")
    try:
        get_llm_client()
        get_rag_engine()
        logger.info("[App] Critical components preloaded successfully.")
    except Exception as e:
        logger.error(f"[App] Preloading failed: {e}")

# Start preloading only if in a Gunicorn worker (to avoid RAM explosion in master)
# or if running directly (flask run / python app.py) WITHOUT the reloader
if (is_gunicorn_worker() or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'):
    import threading
    threading.Thread(target=preload_heavy_components, daemon=True).start()

@socketio.on('connect')
def handle_connect(auth=None):
    """
    Handle Socket.IO connection. 
    Accepts token from 'auth' payload (modern Socket.IO) or cookies.
    """
    token = None
    if auth and 'token' in auth:
        token = auth['token']
    
    if not token:
        token = request.cookies.get('token')
        
    if not token:
        # If no token, we still allow connection for the waiting room to show 'Connected'
        # but the student won't be able to join specific protected rooms without valid SID-to-UID mapping
        logger.warning(f"Socket connected without token: {request.sid}")
        return True

    try:
        # Verify token just to log who connected
        secret = app.config.get('JWT_SECRET_KEY', 'default-secret-key')
        data = jwt.decode(token, secret, algorithms=['HS256'])
        logger.info(f"User {data.get('username')} connected via Socket.IO: {request.sid}")
    except Exception as e:
        logger.warning(f"Socket.IO token validation failed: {e}")
        # We still return True to prevent 401 rejection for now
    
    return True

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Socket disconnected: {request.sid}")

# ... [Keep other routes] ...

@socketio.on('tab_switch')
def handle_tab_switch_event(data):
    session_id = data.get('session_id')
    if session_id:
        # Lightweight logic - handled directly or moved to task
        # Replicating logic here to avoid loading heavy CheatDetector
        result = {
            'suspicious': True,
            'suspicion_score': 100 * 0.10 * 5, 
            'severity': 'HIGH',
            'alert_type': 'TAB_SWITCH',
            'confidence': 1.0,
            'details': {'message': 'User switched tabs or lost focus'}
        }
        
        # Emit alert immediately
        socketio.emit('proctoring_alert', {
            'session_id': session_id,
            'alert_type': result.get('alert_type'),
            'confidence': result.get('confidence'),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'server_time': datetime.utcnow().timestamp(),
            'details': result.get('details')
        }, room='admins')
        
        # Log to DB
        db_manager.log_proctoring_event(session_id, 'TAB_SWITCH', 'high', str(result['details']))

@socketio.on('proctoring_data')
def handle_proctoring_data(data):
    # Process real-time proctoring data ASYNC
    session_id = data.get('session_id')
    frame_data = data.get('frame_data')
    audio_data = data.get('audio_data')
    
    if session_id:
        # Offload to Celery
        celery.send_task('backend.tasks.analyze_frame_task', args=[session_id, frame_data, audio_data])
        
        # Acknowledge receipt (optional, but good for client)
        # emit('ack', {'status': 'received'})

# JWT token authentication - Moved to backend.utils.auth

# Authentication routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'student')
    
    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400
    
    if db_manager.user_exists(username):
        return jsonify({'message': 'Username already exists'}), 400
    
    password_hash = generate_password_hash(password)
    user_id = db_manager.create_user(username, password_hash, role=role)
    
    if not user_id:
        return jsonify({'message': 'Registration failed'}), 500
    
    token = jwt.encode({
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['JWT_SECRET_KEY'])
    
    response = jsonify({'token': token, 'user': {'id': user_id, 'username': username, 'role': role}})
    response.set_cookie(
        'token', 
        token, 
        httponly=True, 
        secure=not app.config['DEBUG'], 
        samesite='Strict',
        max_age=86400
    )
    return response

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400
    
    user_data = db_manager.get_user_by_username(username)
    
    if user_data and check_password_hash(user_data['password_hash'], password):
        token = jwt.encode({
            'user_id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        # Point 3: PyJWT 2.0+ encoding compatibility
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        
        response = jsonify({
            'token': token, 
            'user': {
                'id': user_data['id'], 
                'username': user_data['username'], 
                'role': user_data['role']
            }
        })
        # Point 4: Security improvements for cookies
        response.set_cookie(
            'token', 
            token, 
            httponly=True, 
            secure=not app.config['DEBUG'], 
            samesite='Lax', # Changed from Strict for better UX during navigation
            max_age=86400
        )
        return response
    
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
    # Point 6: Fix extension extraction crash
    if '.' not in filename:
        return jsonify({'message': 'Invalid file name (no extension)'}), 400
    
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
    
    # Point 11: Robust JSON parsing
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    question_count = data.get('question_count', 10)
    difficulty = data.get('difficulty', 'medium')
    topic = data.get('topic', 'General')
    
    if not content:
        return jsonify({'message': 'Content is required'}), 400
    
    try:
        # 1. Generate Questions (Lazy via Provider)
        questions = get_question_generator().generate_questions(content, question_count, difficulty, topic=topic)
        
        # 2. Persist to Question Bank
        saved_questions = []
        for q_data in questions:
            try:
                # Convert dict to Question object
                q_obj = Question(
                    title=f"{topic} Question", # Auto-title
                    question_text=q_data.get('question', ''),
                    question_type=q_data.get('type', 'mcq'),
                    difficulty=q_data.get('difficulty', difficulty),
                    points=q_data.get('points', 1),
                    topic=topic,
                    question_data=q_data, # Store full metadata including options
                    explanation=q_data.get('explanation', ''),
                    created_by=user_id,
                    status='active'
                )
                
                # Save
                q_id = qb_manager.create_question(q_obj)
                if q_id:
                    q_data['db_id'] = q_id # Enrich with DB ID
                    saved_questions.append(q_data)
            except Exception as e:
                # Fallback: return generated question even if save fails
                print(f"Failed to save question: {e}") 
                saved_questions.append(q_data)
                
        return jsonify({'questions': saved_questions})
    except Exception as e:
        return jsonify({'message': f'Question generation failed: {str(e)}'}), 500

@app.route('/api/questions', methods=['GET'])
@token_required
def get_bank_questions(user_id, user_role):
    """List all questions from the bank with filtering."""
    query = request.args.get('query')
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    difficulty = request.args.get('difficulty')
    question_type = request.args.get('type')
    
    filters = {}
    if subject: filters['subject'] = subject
    if topic: filters['topic'] = topic
    if difficulty: filters['difficulty'] = difficulty
    if question_type: filters['question_type'] = question_type
    
    result = qb_manager.search_questions(
        user_id=user_id,
        query=query,
        filters=filters,
        per_page=100 # Large limit for selection
    )
    return jsonify(result)

@app.route('/api/questions/ids', methods=['GET'])
@token_required
def get_bank_question_ids(user_id, user_role):
    """List all question IDs matching the filters (for 'Select All' functionality)."""
    query = request.args.get('query')
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    difficulty = request.args.get('difficulty')
    question_type = request.args.get('type')
    
    filters = {}
    if subject: filters['subject'] = subject
    if topic: filters['topic'] = topic
    if difficulty: filters['difficulty'] = difficulty
    if question_type: filters['question_type'] = question_type
    
    # We use a very large per_page to get all IDs
    result = qb_manager.search_questions(
        user_id=user_id,
        query=query,
        filters=filters,
        per_page=10000 # Effectively "all" for most use cases
    )
    
    ids = [q['id'] for q in result.get('questions', [])]
    return jsonify({'ids': ids})

# Exam management
@app.route('/api/exams', methods=['GET'])
@token_required
def get_exams(user_id, user_role):
    exams = db_manager.get_all_exams()
    return jsonify({'exams': exams})

@app.route('/api/exams/verify/<int:exam_id>', methods=['GET'])
@token_required
def verify_exam(user_id, user_role, exam_id):
    """Verify exam existence and return basic info for student join flow."""
    exam = db_manager.get_exam_by_id(exam_id)
    if not exam:
        return jsonify({'success': False, 'message': 'Exam not found'}), 404
    
    return jsonify({
        'success': True,
        'exam': {
            'id': exam['id'],
            'title': exam['title'],
            'duration': exam['duration'],
            'question_count': len(json.loads(exam['questions']))
        }
    })



def _hydrate_question_from_bank(q_id):
    """Fetch a question by id from the bank and render it in the shape the
    student ExamRoom expects."""
    q_obj = qb_manager.get_question(q_id)
    if not q_obj:
        return None
    data = q_obj.question_data if isinstance(q_obj.question_data, dict) else {}
    return sanitize_question({
        'id': q_obj.id,
        'question_text': q_obj.question_text,
        'question_type': q_obj.question_type,
        'difficulty': q_obj.difficulty,
        'points': q_obj.points,
        'options': data.get('options', {}),
        'correct_answer': data.get('correct_answer') or data.get('answer'),
        'explanation': q_obj.explanation or '',
    })


@app.route('/api/exams', methods=['POST'])
@token_required
def create_exam(user_id, user_role):
    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description', '')
    questions_input = data.get('questions', [])
    # Duration is stored in SECONDS. Accept seconds; reject negative.
    try:
        duration = int(data.get('duration', 3600))
    except (TypeError, ValueError):
        duration = 3600
    if duration <= 0:
        duration = 3600

    if not title or not questions_input:
        return jsonify({'message': 'Title and questions are required'}), 400

    # Normalise: if callers pass IDs, hydrate from bank; otherwise sanitise
    # the inline question shape. Either way the student sees clean data.
    final_questions = []
    for q in questions_input:
        if isinstance(q, int):
            clean = _hydrate_question_from_bank(q)
            if clean:
                final_questions.append(clean)
        elif isinstance(q, dict) and list(q.keys()) == ['id']:
            clean = _hydrate_question_from_bank(q['id'])
            if clean:
                final_questions.append(clean)
        elif isinstance(q, dict):
            clean = sanitize_question(q)
            if clean:
                final_questions.append(clean)

    if not final_questions:
        return jsonify({'message': 'Valid questions are required'}), 400

    exam_id = db_manager.create_exam(title, description, final_questions, duration, user_id)

    if not exam_id:
        return jsonify({'message': 'Exam creation failed'}), 500

    return jsonify({'exam_id': exam_id, 'message': 'Exam created successfully'})

# Exam session management
@app.route('/api/start_exam', methods=['POST'])
@limiter.limit("10 per minute")
@token_required
def start_exam(user_id, user_role):
    data = request.get_json()
    exam_id = data.get('exam_id')
    
    if not exam_id:
        return jsonify({'message': 'Exam ID is required'}), 400
    
    exam = db_manager.get_exam_by_id(exam_id)
    
    if not exam:
        return jsonify({'message': 'Exam not found'}), 404
    
    session_id = db_manager.create_session(exam_id, user_id)
    
    if not session_id:
        return jsonify({'message': 'Session creation failed'}), 500
    
    questions = json.loads(exam['questions'])
    
    return jsonify({
        'session_id': session_id,
        'exam_id': exam_id,
        'exam_title': exam['title'],
        'questions': questions,
        'duration': exam['duration']
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
    
    session = db_manager.get_session(session_id, user_id)
    
    if not session:
        return jsonify({'message': 'Session not found'}), 404
    
    answers = json.loads(session['answers'] or '{}')
    answers[str(question_id)] = answer
    
    db_manager.update_session_answers(session_id, answers)
    
    return jsonify({'message': 'Answer submitted successfully'})

@app.route('/api/end_exam', methods=['POST'])
@token_required
def end_exam(user_id, user_role):
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'message': 'Session ID is required'}), 400
    
    result = db_manager.get_full_session_details(session_id, user_id)
    
    if not result:
        return jsonify({'message': 'Session not found'}), 404
    
    answers = json.loads(result['answers'] or '{}')
    questions = json.loads(result['questions'])
    
    # Grade the exam (Lazy via Provider)
    score = get_grading_engine().grade_exam(questions, answers)
    
    # Update session
    db_manager.complete_session(session_id, score)
    
    return jsonify({'score': score, 'message': 'Exam completed successfully'})

# Proctoring endpoints
@app.route('/api/proctoring_event', methods=['POST'])
@limiter.limit("30 per minute")
@token_required
def log_proctoring_event(user_id, user_role):
    data = request.get_json()
    session_id = data.get('session_id')
    event_type = data.get('event_type')
    severity = data.get('severity', 'low')
    details = data.get('details', '')
    
    if not all([session_id, event_type]):
        return jsonify({'message': 'Session ID and event type are required'}), 400
    
    # Persist to DB so it shows up in Proctoring Logs
    try:
        db_manager.log_proctoring_event(session_id, event_type, severity, str(details))
    except Exception as e:
        logger.error(f"Failed to persist proctoring event: {e}")

    # Emit real-time alert to admins
    socketio.emit('proctoring_alert', {
        'session_id': session_id,
        'event_type': event_type,
        'severity': severity,
        'details': details,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'server_time': datetime.utcnow().timestamp()
    }, room='admins')
    
    return jsonify({'message': 'Event logged successfully'})


@app.route('/api/admin/proctoring-events', methods=['GET'])
@token_required
def get_proctoring_events_list(user_id, user_role):
    """Return persisted proctoring events for the admin Proctoring Logs UI."""
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403

    exam_id = request.args.get('exam_id', type=int)
    session_id = request.args.get('session_id', type=int)
    severity = request.args.get('severity') or None
    limit = request.args.get('limit', default=100, type=int)

    try:
        rows = db_manager.get_proctoring_events(
            exam_id=exam_id,
            session_id=session_id,
            severity=severity,
            limit=limit,
        )
        # Frontend expects field name `student_name`
        events = [
            {
                'id': r.get('id'),
                'session_id': r.get('session_id'),
                'event_type': r.get('event_type'),
                'severity': r.get('severity'),
                'timestamp': r.get('timestamp'),
                'details': r.get('details'),
                'student_name': r.get('username'),
            }
            for r in rows
        ]
        return jsonify({'events': events})
    except Exception as e:
        logger.error(f"Error fetching proctoring events: {e}")
        return jsonify({'message': 'Failed to fetch events', 'events': []}), 500

# Report Export
@app.route('/api/exam/report/<session_id>', methods=['GET'])
@token_required
def download_exam_report(user_id, user_role, session_id):
    format_type = request.args.get('format', 'pdf')
    
    # Get full session details
    session_data = db_manager.get_full_session_details(session_id, user_id)
    if not session_data:
        return jsonify({'message': 'Session not found'}), 404
    
    # Check permissions (student can only see own, admin can see all)
    if user_role != 'admin' and str(session_data.get('user_id')) != str(user_id):
         return jsonify({'message': 'Unauthorized'}), 403

    try:
        # Generate report
        report_output = generate_exam_report(session_data, format_type=format_type)
        
        if format_type == 'json':
            return jsonify(json.loads(report_output))
            
        elif format_type == 'pdf':
            return send_file(
                io.BytesIO(report_output),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"exam_report_{session_id}.pdf"
            )
            
        elif format_type == 'text':
             return Response(report_output, mimetype='text/plain')
             
    except Exception as e:
        return jsonify({'message': f'Report generation failed: {str(e)}'}), 500

# # In-memory store for waiting room students
# Format: {exam_id: {title: "", students: {sid: info}}}
waiting_room_cache = {}
# Track exams that have been started by admin
active_exams_cache = set()

# Admin dashboard endpoints
@app.route('/api/admin/dashboard', methods=['GET'])
@token_required
def admin_dashboard(user_id, user_role):
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    
    active_sessions = db_manager.get_active_sessions_with_details()
    recent_alerts = db_manager.get_recent_alerts(20)
    
    return jsonify({
        'active_sessions': [
            {
                'session_id': session['id'],
                'username': session['username'],
                'exam_title': session['title'],
                'suspicion_score': session['suspicion_score'],
                'started_at': session['started_at']
            }
            for session in active_sessions
        ],
        'recent_alerts': [
            {
                'event_type': alert['event_type'],
                'severity': alert['severity'],
                'timestamp': alert['timestamp'],
                'username': alert['username']
            }
            for alert in recent_alerts
        ],
        'waiting_rooms': [
           {
               'exam_id': eid,
               'title': details.get('title', f"Exam {eid}"),
               'students': [
                   {'id': sid, 'name': sinfo['name'], 'time': sinfo['joined_at']}
                   for sid, sinfo in details.get('students', {}).items()
               ]
           }
           for eid, details in waiting_room_cache.items()
        ]
    })

@app.route('/api/admin/waiting_room', methods=['GET'])
@token_required
def get_waiting_room_status(user_id, user_role):
    """Return the current state of all waiting rooms for the admin."""
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
        
    return jsonify({
        'exams': [
            {
                'id': eid,
                'title': details.get('title', f"Exam {eid}"),
                'status': 'active' if eid in active_exams_cache else 'waiting',
                'students': [
                    {'id': sid, 'name': sinfo['name'], 'time': sinfo['joined_at']}
                    for sid, sinfo in details.get('students', {}).items()
                ]
            }
            for eid, details in waiting_room_cache.items()
        ]
    })

@app.route('/api/admin/unlock_exam', methods=['POST'])
@token_required
def unlock_exam(user_id, user_role):
    """Admin allows students in the waiting room to start the test."""
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
        
    data = request.get_json()
    exam_id = str(data.get('exam_id'))
    
    if not exam_id:
        return jsonify({'message': 'Exam ID is required'}), 400
        
    # Add to active exams cache
    active_exams_cache.add(exam_id)
    logger.info(f"Exam {exam_id} unlocked by Admin {user_id}")
    
    # Notify students via Socket.IO
    socketio.emit('exam_unlocked', {'exam_id': exam_id}, room=f"exam_{exam_id}")
    
    return jsonify({'message': f'Exam {exam_id} unlocked successfully', 'status': 'active'})

@app.route('/api/exams/<int:exam_id>', methods=['GET'])
@token_required
def get_exam_details(user_id, user_role, exam_id):
    """Return full exam details including questions."""
    exam = db_manager.get_exam_by_id(exam_id)
    if not exam:
        return jsonify({'message': 'Exam not found'}), 404
    
    questions = json.loads(exam['questions'])
    
    # Check if exam is already started/unlocked
    is_unlocked = str(exam_id) in active_exams_cache
    
    if not is_unlocked and user_role == 'student':
        return jsonify({
            'message': 'This exam is currently locked. Please wait for the instructor to start it.',
            'title': exam['title'],
            'unlocked': False
        }), 403

    return jsonify({
        'id': exam['id'],
        'title': exam['title'],
        'duration': exam['duration'],
        'questions': questions,
        'totalMarks': len(questions) * 1,
        'unlocked': True
    })

# WebSocket events
@socketio.on('join_admin')
def on_join_admin():
    join_room('admins')
    emit('status', {'message': 'Connected to admin dashboard'})

@socketio.on('join_exam_room')
def handle_join_exam_room(data):
    """Student joins the waiting room for a specific exam."""
    exam_id = str(data.get('exam_id'))
    student_id = str(data.get('student_id'))
    student_name = data.get('student_name', 'Unknown Student')
    
    if exam_id:
        room = f"exam_{exam_id}"
        join_room(room)
        
        # Get exam title for the admin dashboard grouping
        exam = db_manager.get_exam_by_id(exam_id)
        exam_title = exam['title'] if exam else f"Exam {exam_id}"
        
        # Update cache
        if exam_id not in waiting_room_cache:
            waiting_room_cache[exam_id] = {'title': exam_title, 'students': {}}
        
        waiting_room_cache[exam_id]['students'][student_id] = {
            'name': student_name,
            'joined_at': datetime.utcnow().isoformat()
        }
        
        # Notify admins that a new student joined
        socketio.emit('student_joined', {
            'exam_id': exam_id,
            'exam_title': exam_title,
            'student_id': student_id,
            'student_name': student_name,
            'timestamp': datetime.utcnow().isoformat()
        }, room='admins')

@socketio.on('admin_start_exam')
def handle_admin_start_exam(data):
    """Admin clicks Start Exam, broadcasting signal to waiting students."""
    exam_id = str(data.get('exam_id'))
    if exam_id:
        # Mark as active
        active_exams_cache.add(exam_id)
        
        # Clear from waiting cache
        if exam_id in waiting_room_cache:
            del waiting_room_cache[exam_id]
            
        socketio.emit('exam_started', {
            'exam_id': exam_id,
            'message': 'The exam has started',
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"exam_{exam_id}")

@socketio.on('join_session')
def on_join_session(data):
    session_id = data.get('session_id')
    if session_id:
        join_room(f'session_{session_id}')
        emit('status', {'message': f'Joined session {session_id}'})


# ============================================================
# WebRTC Signaling for Interview Rooms
# ============================================================

@socketio.on('join_interview_room')
def handle_join_interview_room(data):
    """Join a WebRTC interview room for signaling."""
    room_id = data.get('room_id')
    username = data.get('username', 'Anonymous')
    if not room_id:
        return
    room = f'interview_{room_id}'
    join_room(room)
    logger.info(f"[WebRTC] {username} joined interview room {room_id}")
    emit('peer_joined', {'peer_id': request.sid, 'username': username}, room=room, include_self=False)
    emit('status', {'message': f'Joined interview room {room_id}'})


@socketio.on('leave_interview_room')
def handle_leave_interview_room(data):
    room_id = data.get('room_id')
    if not room_id:
        return
    room = f'interview_{room_id}'
    leave_room(room)
    emit('peer_left', {'peer_id': request.sid}, room=room, include_self=False)


@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    room_id = data.get('room_id')
    emit('webrtc_offer', {'offer': data.get('offer'), 'from_peer': request.sid},
         room=f'interview_{room_id}', include_self=False)


@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    room_id = data.get('room_id')
    emit('webrtc_answer', {'answer': data.get('answer'), 'from_peer': request.sid},
         room=f'interview_{room_id}', include_self=False)


@socketio.on('webrtc_ice_candidate')
def handle_ice_candidate(data):
    room_id = data.get('room_id')
    emit('webrtc_ice_candidate', {'candidate': data.get('candidate'), 'from_peer': request.sid},
         room=f'interview_{room_id}', include_self=False)


@socketio.on('screen_share_started')
def handle_screen_share_started(data):
    room_id = data.get('room_id')
    emit('screen_share_started', {'peer_id': request.sid}, room=f'interview_{room_id}', include_self=False)


@socketio.on('screen_share_stopped')
def handle_screen_share_stopped(data):
    room_id = data.get('room_id')
    emit('screen_share_stopped', {'peer_id': request.sid}, room=f'interview_{room_id}', include_self=False)


@app.route('/api/proctoring_frame', methods=['POST'])
@limiter.limit("12 per minute")
@token_required
def handle_proctoring_frame(user_id, user_role):
    data = request.get_json()
    session_id = data.get('session_id')
    frame_data = data.get('frame_data')
    
    if not session_id or not frame_data:
        return jsonify({'message': 'Missing session_id or frame_data'}), 400

    try:
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
            
            # Also emit to the specific session room so the student gets a warning if needed
            socketio.emit('proctoring_alert', {
                'session_id': session_id,
                'alert_type': analysis_result.get('alert_type'),
                'details': 'Suspicious behavior detected'
            }, room=f'session_{session_id}')

        return jsonify(analysis_result), 200
    except Exception as e:
        logger.error(f"Error processing proctoring frame: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'message': 'Internal server error processing frame'}), 500


# ==================== QUESTION GENERATION ENDPOINTS ====================

from backend.services.question_generation_service import get_question_generation_service

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/questions/generate/ai', methods=['POST'])
@token_required
def generate_questions_ai(user_id, user_role):
    """
    Generate questions using pure AI (no document upload)
    ---
    tags:
      - Questions
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            topic:
              type: string
              required: true
            count:
              type: integer
              default: 10
            difficulty:
              type: string
              enum: [easy, medium, hard, expert]
            types:
              type: array
              items:
                type: string
            bank_id:
              type: integer
    responses:
      200:
        description: Questions generated successfully
    """
    data = request.get_json()
    
    topic = data.get('topic')
    if not topic:
        return jsonify({'success': False, 'message': 'Topic is required'}), 400
    
    count = data.get('count', 10)
    difficulty = data.get('difficulty', 'medium')
    question_types = data.get('types', ['mcq'])
    bank_id = data.get('bank_id')
    
    try:
        service = get_question_generation_service()
        result = service.generate_pure_ai(
            topic=topic,
            count=count,
            difficulty=difficulty,
            question_types=question_types,
            bank_id=bank_id,
            user_id=user_id
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error generating AI questions: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/questions/generate/rag', methods=['POST'])
@token_required
def generate_questions_rag(user_id, user_role):
    """
    Generate questions from uploaded document using RAG
    ---
    tags:
      - Questions
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
      - in: formData
        name: topic
        type: string
      - in: formData
        name: count
        type: integer
      - in: formData
        name: difficulty
        type: string
      - in: formData
        name: bank_id
        type: integer
    responses:
      200:
        description: Questions generated from document
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'File type not allowed. Use PDF or DOCX'}), 400
    
    # Save file temporarily
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    try:
        topic = request.form.get('topic', 'Document Content')
        count = int(request.form.get('count', 10))
        difficulty = request.form.get('difficulty', 'medium')
        question_types = request.form.getlist('types') or ['mcq']
        bank_id = request.form.get('bank_id')
        if bank_id:
            bank_id = int(bank_id)
        
        service = get_question_generation_service()
        result = service.generate_rag(
            file_path=file_path,
            topic=topic,
            count=count,
            difficulty=difficulty,
            question_types=question_types,
            bank_id=bank_id,
            user_id=user_id
        )
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in RAG generation: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.route('/api/questions/scan', methods=['POST'])
@limiter.limit("5 per minute")
@token_required
def scan_questions_pdf(user_id, user_role):
    """
    Scan existing question PDF and extract questions
    ---
    tags:
      - Questions
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
      - in: formData
        name: topic
        type: string
      - in: formData
        name: bank_id
        type: integer
    responses:
      200:
        description: Questions extracted from PDF
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'File type not allowed. Use PDF'}), 400
    
    # Save file temporarily
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    try:
        topic = request.form.get('topic', 'Extracted Questions')
        bank_id = request.form.get('bank_id')
        if bank_id:
            bank_id = int(bank_id)
        
        service = get_question_generation_service()
        result = service.scan_pdf(
            file_path=file_path,
            topic=topic,
            bank_id=bank_id,
            user_id=user_id
        )
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error scanning questions: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


# ============================================================
# INTERVIEW ENDPOINTS
# ============================================================

# In-memory interview sessions store
# Production: move to DB table
interview_sessions = {}

@app.route('/api/interviews', methods=['POST'])
@token_required
def create_interview(user_id, user_role):
    """Admin creates an interview session."""
    if user_role not in ('admin', 'teacher'):
        return jsonify({'message': 'Admin/teacher access required'}), 403

    data = request.get_json() or {}
    title = data.get('title', 'Interview Session')
    candidate_name = data.get('candidate_name', '')
    scheduled_at = data.get('scheduled_at', '')

    import uuid
    session_id = uuid.uuid4().hex[:12]

    interview_sessions[session_id] = {
        'id': session_id,
        'title': title,
        'candidate_name': candidate_name,
        'scheduled_at': scheduled_at,
        'created_by': user_id,
        'status': 'waiting',  # waiting, active, completed
        'participants': [],
    }

    return jsonify({
        'success': True,
        'session_id': session_id,
        'join_url': f'/student/interview/{session_id}',
        'message': f'Interview created. Share session ID: {session_id}'
    }), 201


@app.route('/api/interviews', methods=['GET'])
@token_required
def list_interviews(user_id, user_role):
    """List all interview sessions (admin view)."""
    if user_role not in ('admin', 'teacher'):
        return jsonify({'message': 'Admin/teacher access required'}), 403

    sessions = list(interview_sessions.values())
    return jsonify({'interviews': sessions})


@app.route('/api/interviews/<session_id>', methods=['GET'])
@token_required
def get_interview(user_id, user_role, session_id):
    """Get interview session details (for both admin and candidate)."""
    session = interview_sessions.get(session_id)
    if not session:
        # Return a minimal session so the room can still load
        return jsonify({
            'id': session_id,
            'title': 'Interview Session',
            'status': 'active',
        })

    return jsonify(session)


@app.route('/api/interviews/<session_id>/join', methods=['POST'])
@token_required
def join_interview(user_id, user_role, session_id):
    """Candidate or interviewer joins the session."""
    session = interview_sessions.get(session_id)
    if not session:
        interview_sessions[session_id] = {
            'id': session_id,
            'title': 'Interview Session',
            'status': 'active',
            'participants': [],
            'created_by': user_id,
        }
        session = interview_sessions[session_id]

    # Add participant
    participant = {'user_id': user_id, 'role': user_role, 'joined_at': datetime.utcnow().isoformat()}
    if not any(p['user_id'] == user_id for p in session['participants']):
        session['participants'].append(participant)

    session['status'] = 'active'

    return jsonify({
        'success': True,
        'session': session,
        'message': 'Joined interview session'
    })


@app.route('/api/interviews/<session_id>/end', methods=['POST'])
@token_required
def end_interview(user_id, user_role, session_id):
    """End an interview session."""
    session = interview_sessions.get(session_id)
    if session:
        session['status'] = 'completed'

    return jsonify({'success': True, 'message': 'Interview ended'})


if __name__ == '__main__':
    with app.app_context():
        db_manager.init_database()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
