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

from backend.questions import QuestionGenerator
from backend.grading import GradingEngine

from backend.utils.pdf_parser import parse_pdf
from backend.utils.docx_parser import parse_docx
from backend.utils.report_export import generate_exam_report
from backend.config import Config
from backend.db.database import DatabaseManager

app = Flask(__name__)
app.config.from_object(Config)
# Initialize Flasgger
swagger = Swagger(app)

CORS(app, origins=app.config['CORS_ORIGINS'])
socketio = SocketIO(
    app, 
    cors_allowed_origins=app.config['CORS_ORIGINS'],
    message_queue=app.config['CELERY_BROKER_URL'],
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Initialize components
question_generator = QuestionGenerator()
grading_engine = GradingEngine()
from backend.question_bank import QuestionBankManager, Question # Import Question models

db_manager = DatabaseManager('sqlite:///exam_platform.db')
qb_manager = QuestionBankManager('exam_platform.db')

from backend.celery_app import celery

# Initialize CheatDetector
from backend.models.cheat_detector import CheatDetector
cheat_detector = CheatDetector()

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
        }, app.config['JWT_SECRET_KEY'])
        
        response = jsonify({
            'token': token, 
            'user': {
                'id': user_data['id'], 
                'username': user_data['username'], 
                'role': user_data['role']
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
        questions = question_generator.generate_questions(content, question_count, difficulty, topic=topic)
        
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

# Exam management
@app.route('/api/exams', methods=['GET'])
@token_required
def get_exams(user_id, user_role):
    exams = db_manager.get_all_exams()
    return jsonify({'exams': exams})

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
    
    exam_id = db_manager.create_exam(title, description, questions, duration, user_id)
    
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
    
    exam = db_manager.get_exam_by_id(exam_id)
    
    if not exam:
        return jsonify({'message': 'Exam not found'}), 404
    
    session_id = db_manager.create_session(exam_id, user_id)
    
    if not session_id:
        return jsonify({'message': 'Session creation failed'}), 500
    
    questions = json.loads(exam['questions'])
    
    return jsonify({
        'session_id': session_id,
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
    
    # Grade the exam
    score = grading_engine.grade_exam(questions, answers)
    
    # Update session
    db_manager.complete_session(session_id, score)
    
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
@jwt_required()
def handle_proctoring_frame():
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


@app.route('/api/questions/scan', methods=['POST'])
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


if __name__ == '__main__':
    with app.app_context():
        db_manager.init_database()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
