import os
import json
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import jwt
import io
from flask import Flask, request, jsonify, send_file, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flasgger import Swagger
from backend.utils.auth import token_required
from backend.utils.logging_config import setup_logging

# Initialize Logging
setup_logging(name="app", log_file="server.log")

# Imports moved to lazy accessors to prevent heavy module loading
# from backend.engine.questions import QuestionGenerator
# from backend.engine.grading import GradingEngine

from backend.utils.pdf_parser import parse_pdf
from backend.utils.docx_parser import parse_docx
from backend.utils.report_export import generate_exam_report
from backend.config import Config
from backend.engine.question_bank import Question 
from backend.models.schema import db, Exam, Session

app = Flask(__name__)
app.config.from_object(Config)

# Ensure SQLAlchemy URI is set (maps from Config.DATABASE_URL)
app.config['SQLALCHEMY_DATABASE_URI'] = app.config.get('SQLALCHEMY_DATABASE_URI') or Config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

# Initialize Flasgger
swagger = Swagger(app)

CORS(app, origins=app.config['CORS_ORIGINS'])
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    message_queue=app.config.get('CELERY_BROKER_URL'),
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True,
    async_mode='threading'
)

# Lazy Loading Components
_question_generator = None
_grading_engine = None
_db_manager = None
_qb_manager = None
_cheat_detector = None

def get_question_generator():
    global _question_generator
    if _question_generator is None:
        print("Lazy loading QuestionGenerator...")
        from backend.engine.questions import QuestionGenerator
        _question_generator = QuestionGenerator()
    return _question_generator

def get_grading_engine():
    global _grading_engine
    if _grading_engine is None:
        print("Lazy loading GradingEngine...")
        from backend.engine.grading import GradingEngine
        _grading_engine = GradingEngine()
    return _grading_engine

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        print("Lazy loading DatabaseManager...")
        from backend.db.database import DatabaseManager # Local import to avoid circular dependency if any
        _db_manager = DatabaseManager('sqlite:///exam_platform.db')
    return _db_manager

def get_qb_manager():
    """Lazy load QuestionBankManager"""
    global _qb_manager
    if _qb_manager is None:
        print("Lazy loading QuestionBankManager...")
        from backend.engine.question_bank import QuestionBankManager
        _qb_manager = QuestionBankManager('exam_platform.db')
    return _qb_manager

def get_cheat_detector():
    """Lazy load CheatDetector"""
    global _cheat_detector
    if _cheat_detector is None:
        print("Lazy loading CheatDetector...")
        from backend.models.cheat_detector import CheatDetector
        _cheat_detector = CheatDetector()
    return _cheat_detector

# Accessors for usage in routes
db_manager = None # Deprecated: Use get_db_manager() internally but keep name for now/refactor
qb_manager = None 
cheat_detector = None

from backend.celery_app import celery


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

@socketio.on('join_exam_room')
def handle_join_exam_room(data):
    """Student joins the waiting room for a specific exam."""
    exam_id = data.get('exam_id')
    student_id = data.get('student_id')
    student_name = data.get('student_name', 'Unknown Student')
    
    if exam_id:
        room = f"exam_{exam_id}"
        join_room(room)
        print(f"Student {student_id} ({student_name}) joined room: {room}")
        
        # Notify admins that a new student joined
        emit('student_joined', {
            'exam_id': exam_id,
            'student_id': student_id,
            'student_name': student_name,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)

@socketio.on('admin_start_exam')
def handle_admin_start_exam(data):
    """Admin clicks Start Exam, broadcasting signal to all waiting students."""
    exam_id = data.get('exam_id')
    if exam_id:
        room = f"exam_{exam_id}"
        print(f"Admin triggered start for room: {room}")
        emit('exam_started', {
            'exam_id': exam_id,
            'message': 'The exam has started',
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)


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
        get_db_manager().log_proctoring_event(session_id, 'TAB_SWITCH', 'high', str(result['details']))

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
    
    if get_db_manager().user_exists(username):
        return jsonify({'message': 'Username already exists'}), 400
    
    password_hash = generate_password_hash(password)
    user_id = get_db_manager().create_user(username, password_hash, role=role)
    
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
    
    user_data = get_db_manager().get_user_by_username(username)
    
    if user_data and check_password_hash(user_data.password_hash, password):
        token = jwt.encode({
            'user_id': user_data.id,
            'username': user_data.username,
            'role': user_data.role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['JWT_SECRET_KEY'])
        
        response = jsonify({
            'token': token, 
            'user': {
                'id': user_data.id, 
                'username': user_data.username, 
                'role': user_data.role
            }
        })
        response.set_cookie(
            'token', 
            token, 
            httponly=True, 
            secure=not app.config['DEBUG'], 
            samesite='Strict',
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
    topic = data.get('topic', 'General')
    
    if not content:
        return jsonify({'message': 'Content is required'}), 400
    
    try:
        # 1. Generate Questions
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
                q_id = get_qb_manager().create_question(q_obj)
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

# Exam management
@app.route('/api/exams', methods=['GET'])
@token_required
def get_exams(user_id, user_role):
    exams = get_db_manager().get_all_exams()
    return jsonify({'exams': [{'id': e.id, 'title': e.title, 'description': e.description, 'duration': e.duration} for e in exams]})

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
    
    exam_id = get_db_manager().create_exam(title, description, questions, duration, user_id)
    
    if not exam_id:
        return jsonify({'message': 'Exam creation failed'}), 500
    
    return jsonify({'exam_id': exam_id, 'message': 'Exam created successfully'})

# Exam session management
@app.route('/api/start_exam', methods=['POST'])
@token_required
def start_exam(user_id, user_role):
    data = request.get_json()
    exam_id = data.get('exam_id')
    
    if not exam_id:
        return jsonify({'message': 'Exam ID is required'}), 400
    
    exam = get_db_manager().get_exam_by_id(exam_id)
    
    if not exam:
        return jsonify({'message': 'Exam not found'}), 404
    
    session_id = get_db_manager().create_session(exam_id, user_id)
    
    if not session_id:
        return jsonify({'message': 'Session creation failed'}), 500
    
    questions = json.loads(exam.questions)
    
    return jsonify({
        'session_id': session_id,
        'exam_title': exam.title,
        'questions': questions,
        'duration': exam.duration
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
    
    session = get_db_manager().get_session(session_id, user_id)
    
    if not session:
        return jsonify({'message': 'Session not found'}), 404
    
    answers = json.loads(session.answers or '{}')
    answers[str(question_id)] = answer
    
    get_db_manager().update_session_answers(session_id, answers)
    
    return jsonify({'message': 'Answer submitted successfully'})

@app.route('/api/end_exam', methods=['POST'])
@token_required
def end_exam(user_id, user_role):
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'message': 'Session ID is required'}), 400
    
    result = get_db_manager().get_full_session_details(session_id, user_id)
    
    if not result:
        return jsonify({'message': 'Session not found'}), 404
    
    answers = json.loads(result['answers'] or '{}')
    questions = json.loads(result['questions'])
    
    # Grade the exam
    score = get_grading_engine().grade_exam(questions, answers)
    
    # Update session
    get_db_manager().complete_session(session_id, score)
    
    return jsonify({'score': score, 'message': 'Exam completed successfully'})

@app.route('/api/exams', methods=['POST'])
@token_required
def create_exam_endpoint(user_id, user_role):
    """Create a new exam from a list of questions"""
    data = request.get_json()
    title = data.get('title')
    description = data.get('description', '')
    questions = data.get('questions')
    duration = data.get('duration', 60)
    
    if not title:
        return jsonify({'message': 'Title is required'}), 400
    if not questions or not isinstance(questions, list):
        return jsonify({'message': 'Questions list is required'}), 400
        
    exam_id = get_db_manager().create_exam(
        title=title,
        description=description,
        questions=questions,
        duration=duration,
        created_by=user_id
    )
    
    if exam_id:
        return jsonify({
            'message': 'Exam created successfully',
            'exam_id': exam_id
        }), 201
    else:
        return jsonify({'message': 'Failed to create exam'}), 500

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

# Report Export
@app.route('/api/exam/report/<session_id>', methods=['GET'])
@token_required
def download_exam_report(user_id, user_role, session_id):
    format_type = request.args.get('format', 'pdf')
    
    # Get full session details
    session_data = get_db_manager().get_full_session_details(session_id, user_id)
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

# Admin dashboard endpoints
@app.route('/api/admin/dashboard', methods=['GET'])
@token_required
def admin_dashboard(user_id, user_role):
    if user_role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    
    active_sessions = get_db_manager().get_active_sessions_with_details()
    recent_alerts = get_db_manager().get_recent_alerts(20)
    
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

@app.route('/api/proctoring_frame', methods=['POST'])
@token_required
def handle_proctoring_frame(user_id, user_role):
    data = request.get_json()
    session_id = data.get('session_id')
    frame_data = data.get('frame_data')
    
    if not session_id or not frame_data:
        return jsonify({'message': 'Missing session_id or frame_data'}), 400

    try:
        # Analyze frame for suspicious activity
        analysis_result = get_cheat_detector().analyze_frame(frame_data)
        
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
        import traceback
        traceback.print_exc()
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
def generate_questions_ai(current_user):
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
    
    # ... existing implementation (omitted for brevity) ...
    return jsonify({'message': 'Please use Universal Engine (/api/generate_questions_universal)'})

@app.route('/api/generate_questions_universal', methods=['POST'])
@token_required
def generate_questions_universal(current_user, user_role):
    """
    Async generation endpoint compatible with smoke tests.
    Dispatches to Celery task.
    """
    data = request.get_json()
    
    print("DEBUG: Received request", flush=True)
    # Dispatch task
    # Lazy import to avoid circular dependency
    print("DEBUG: Importing generation_tasks...", flush=True)
    from backend.engine.generation_tasks import generate_batch_task
    print("DEBUG: Imported. Calling delay...", flush=True)
    
    task = generate_batch_task.delay(data)
    print("DEBUG: Task dispatched. ID:", task.id, flush=True)
    
    return jsonify({
        'job_id': task.id,
        'message': 'Generation started',
        'status': 'queued'
    })

@app.route('/api/generation_status/<job_id>', methods=['GET'])
@token_required
def get_generation_status(current_user, user_role, job_id):
    """
    Check status of async generation job.
    """
    from celery.result import AsyncResult
    from backend.celery_app import celery
    
    task_result = AsyncResult(job_id, app=celery)
    
    response = {
        'status': task_result.status.lower(),
        'job_id': job_id
    }
    
    if task_result.state == 'PENDING':
        response.update({'progress': 0, 'total': 100})
    elif task_result.state == 'PROCESSING':
        meta = task_result.info or {}
        response.update({
             'status': 'processing',
             'progress': meta.get('current', 0),
             'total': meta.get('total', 100)
        })
    elif task_result.state == 'SUCCESS':
        # Celery uses SUCCESS, we map to 'completed' for smoke test
        result = task_result.result or {}
        response.update({
            'status': 'completed',
            'result': result,
            'progress': 100,
            'total': 100
        })
    elif task_result.state == 'FAILURE':
        response.update({
            'status': 'failed',
            'error': str(task_result.result)
        })
        
    return jsonify(response)
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
            user_id=current_user.get('id')
        )
        return jsonify(result), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/questions/generate/rag', methods=['POST'])
@token_required
def generate_questions_rag(current_user):
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
            user_id=current_user.get('id')
        )
        return jsonify(result), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


# ==================== QUESTION BANK ROUTES ====================

@app.route('/api/question-bank/questions', methods=['GET'])
@token_required
def get_question_bank_questions(user_id, user_role):
    """
    Get paginated and filtered questions from the bank
    ---
    tags:
      - Question Bank
    parameters:
      - in: query
        name: page
        type: integer
      - in: query
        name: per_page
        type: integer
      - in: query
        name: topic
        type: string
      - in: query
        name: type
        type: string
      - in: query
        name: difficulty
        type: string
    responses:
      200:
        description: List of questions
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        filters = {}
        if request.args.get('topic'):
            filters['topic'] = request.args.get('topic')
        if request.args.get('type'):
            filters['question_type'] = request.args.get('type')
        if request.args.get('difficulty'):
            filters['difficulty'] = request.args.get('difficulty')
            
        # Get questions for current user (or public ones)
        # Note: QuestionBankManager needs initialized with db path
        qb_manager = get_qb_manager()
        result = qb_manager.search_questions(
            user_id=user_id,
            filters=filters,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'questions': result['questions'],
            'pages': result['pagination']['total_pages'],
            'total': result['pagination']['total_count']
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@token_required
def scan_questions_pdf(current_user):
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
            user_id=current_user.get('id')
        )
        return jsonify(result), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


# ==================== STUDENT-FACING ROUTES ====================

@app.route('/api/student/dashboard', methods=['GET', 'OPTIONS'])
@token_required
def student_dashboard(user_id, user_role):
    """Get student dashboard data including available exams."""
    try:
        # Get available exams
        exams = Exam.query.all()
        exam_list = []
        for exam in exams:
            questions = json.loads(exam.questions) if exam.questions else []
            exam_list.append({
                'id': exam.id,
                'title': exam.title,
                'description': exam.description,
                'question_count': len(questions),
                'duration': exam.duration,
                'created_at': exam.created_at.isoformat() if exam.created_at else None
            })
        
        # Get student's sessions
        sessions = Session.query.filter_by(user_id=user_id).all()
        session_list = [{
            'id': s.id,
            'exam_id': s.exam_id,
            'status': s.status,
            'score': s.score,
            'started_at': s.started_at.isoformat() if s.started_at else None,
            'completed_at': s.completed_at.isoformat() if s.completed_at else None
        } for s in sessions]
        
        return jsonify({
            'exams': exam_list,
            'sessions': session_list,
            'user': {'id': user_id, 'role': user_role}
        })
    except Exception as e:
        logger.error(f"Student dashboard error: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/api/exams/<int:exam_id>', methods=['GET', 'OPTIONS'])
@token_required
def get_exam_detail(user_id, user_role, exam_id):
    """Get exam details by ID including questions."""
    try:
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({'message': 'Exam not found'}), 404
        
        questions = json.loads(exam.questions) if exam.questions else []
        
        return jsonify({
            'id': exam.id,
            'title': exam.title,
            'description': exam.description,
            'questions': questions,
            'duration': exam.duration,
            'question_count': len(questions),
            'created_at': exam.created_at.isoformat() if exam.created_at else None
        })
    except Exception as e:
        logger.error(f"Get exam error: {e}")
        return jsonify({'message': str(e)}), 500


@app.route('/api/student/available-exams', methods=['GET', 'OPTIONS'])
@token_required
def get_available_exams(user_id, user_role):
    """Get list of available exams for students."""
    try:
        exams = Exam.query.all()
        exam_list = []
        for exam in exams:
            questions = json.loads(exam.questions) if exam.questions else []
            exam_list.append({
                'id': exam.id,
                'name': exam.title,
                'title': exam.title,
                'description': exam.description,
                'duration': f"{exam.duration // 60} min" if exam.duration else "60 min",
                'question_count': len(questions),
                'status': 'Ready',
                'color': 'green',
                'date': exam.created_at.strftime('%b %d, %Y') if exam.created_at else 'N/A'
            })
        
        return jsonify({'exams': exam_list})
    except Exception as e:
        logger.error(f"Available exams error: {e}")
        return jsonify({'message': str(e)}), 500


if __name__ == '__main__':
    try:
        print("Initializing database...")
        with app.app_context():
            get_db_manager().init_database()
        print("Starting Flask-SocketIO server on port 5000...")
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
        print("SERVER EXITED (socketio.run returned)")
    except Exception as e:
        print(f"CRITICAL ERROR STARTING SERVER: {e}")
        import traceback
        traceback.print_exc()
        print("Press Enter to exit...")
        input()
