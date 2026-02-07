
import os
import io
import json
import logging
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from backend.config import Config
from backend.db.database import DatabaseManager
from backend.utils.redis_manager import redis_manager
# from backend.tasks import process_pdf_exam_task # Circular import risk if tasks imports app
# We will use string name for celery task to avoid import cycle

from backend.app import token_required # Helper decorator (might be circular if not careful)
# If app.py imports this file, we can't import app.py.
# We should redefine token_required or move it to a shared auth module.
# For now, I'll copy the decorator logic or assume the user refactors auth.
# To play safe, I will implement a local 'admin_required' decorator using decode logic.

import jwt
from functools import wraps

logger = logging.getLogger(__name__)

pdf_bp = Blueprint('pdf_api', __name__)

# Helper for DB access
def get_db():
    return DatabaseManager(Config.DATABASE_URL)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            token = request.cookies.get('token')
        if not token:
            return jsonify({'message': 'Token missing'}), 401
        
        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            if data['role'] != 'admin':
                return jsonify({'message': 'Admin access required'}), 403
            return f(data['user_id'], *args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Invalid token'}), 401
    return decorated

@pdf_bp.route('/api/admin/pdf/upload', methods=['POST'])
@admin_required
def upload_pdf_exam(user_id):
    """
    Step 1: Upload PDF -> Start Async Pipeline
    """
    if 'file' not in request.files:
        return jsonify({'message': 'No file uploaded'}), 400
        
    file = request.files['file']
    if not file.filename.endswith('.pdf'):
        return jsonify({'message': 'PDF only'}), 400
        
    # Save file
    safe_name = secure_filename(file.filename)
    upload_dir = os.path.join('backend', 'uploads', 'exams')
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_name)
    file.save(file_path)
    
    # Create Exam Record (Draft)
    db = get_db()
    exam_id = db.create_exam(
        title=f"PDF Exam: {safe_name}",
        description="Encrypted PDF Exam (Processing)",
        questions=[], # Empty initially
        duration=3600,
        creator_id=user_id
    )
    
    # Update source type
    # (create_exam doesn't support source_type arg yet, assume default update)
    conn = db.get_connection()
    conn.execute("UPDATE exams SET source_type = 'pdf_extracted' WHERE id = ?", (exam_id,))
    conn.commit()
    conn.close()
    
    # Trigger Task
    job_id = f"pdf_job_{exam_id}"
    
    # Import celery here to avoid top-level cycle
    from backend.celery_app import celery
    celery.send_task('backend.tasks.process_pdf_exam_task', args=[job_id, file_path, exam_id])
    
    return jsonify({
        "message": "Upload successful. Processing started.",
        "job_id": job_id,
        "exam_id": exam_id
    })

@pdf_bp.route('/api/admin/pdf/status/<job_id>', methods=['GET'])
@admin_required
def get_pdf_status(user_id, job_id):
    """Check Redis for progress"""
    status = redis_manager.get_job_status(job_id)
    if not status:
        return jsonify({"message": "Job not found"}), 404
    return jsonify(status)

@pdf_bp.route('/api/admin/pdf/review/<job_id>', methods=['GET'])
@admin_required
def review_pdf_result(user_id, job_id):
    """Fetch generated results for Admin Review"""
    # Results are stored in Redis key 'job:{id}:result' by RedisManager.set_job_completed
    # But RedisManager stores it as stringified JSON in 'result' field of the hash?
    # No, set_job_completed sets "job:{id}:result" key separately! (Line 207 of redis_manager.py)
    
    client = redis_manager.client
    if not client:
        return jsonify({"message": "Redis unavailable"}), 500
        
    res_key = f"job:{job_id}:result"
    data = client.get(res_key)
    
    if not data:
        # Check if job failed?
        err_key = f"job:{job_id}:error"
        err = client.get(err_key)
        if err:
            return jsonify({"status": "failed", "error": err}), 400
        return jsonify({"message": "Result not ready"}), 404
        
    return jsonify(json.loads(data))

@pdf_bp.route('/api/admin/pdf/finalize', methods=['POST'])
@admin_required
def finalize_pdf_exam(user_id):
    """
    Step 9: Commit Admin Approved Links to Secure DB
    Input: { "exam_id": 1, "approved_links": [ ... ] }
    """
    data = request.get_json()
    exam_id = data.get('exam_id')
    approved_links = data.get('approved_links', [])
    
    if not exam_id or not approved_links:
        return jsonify({"message": "Missing data"}), 400
        
    db = get_db()
    success_count = 0
    
    for link in approved_links:
        q_data = link['question']
        a_data = link['answer']
        
        # Ensure ID
        if 'question_id' not in q_data:
            q_data['question_id'] = f"q_{uuid.uuid4().hex[:8]}"
            
        success = db.save_pdf_exam_pair(
            exam_id=str(exam_id),
            question_data=q_data,
            answer_data={
                "correct_answer": a_data.get('text', ''), # Assuming text is the answer
                "explanation": "Extracted from PDF", 
                "confidence": link.get('confidence', 1.0),
                "source_page": a_data.get('page'),
                "source_chunk_id": a_data.get('chunk_id')
            },
            admin_id=user_id
        )
        if success:
            success_count += 1
            
    # Mark exam as Active
    conn = db.get_connection()
    conn.execute("UPDATE exams SET status = 'active' WHERE id = ?", (exam_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": "Exam finalized successfully",
        "saved_count": success_count
    })
