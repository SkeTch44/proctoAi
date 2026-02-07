from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from functools import wraps
import sqlite3
import json
import jwt

from config import Config
from db.database import DatabaseManager

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
app.config.from_object(Config)

db = DatabaseManager("sqlite:///exam_platform.db")
db.init_database()
db.migrate_schema()

# JWT DECORATOR
def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"message": "Token missing"}), 401
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        return f(payload["user_id"], payload["role"], *args, **kwargs)
    return wrapper

# ROLE DECORATOR
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(user_id, role, *args, **kwargs):
            if role != required_role:
                return jsonify({"message": "Access denied"}), 403
            return f(user_id, role, *args, **kwargs)
        return wrapper
    return decorator

# AUTH - LOGIN
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON"}), 400
    user = db.authenticate_user(data.get("username") or data.get("email"), data.get("password") or "")
    if not user:
        return jsonify({"message": "Invalid credentials"}), 401
    token = jwt.encode({
        "user_id": user["id"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }, app.config["JWT_SECRET_KEY"], algorithm="HS256")
    return jsonify({"token": token, "user": user})

# AUTH - REGISTER (FULL NAME REQUIRED) ✅
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON"}), 400

    username = data.get("username")
    full_name = data.get("full_name") 
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "student")

    # FULL NAME IS COMPULSORY ✅
    if not username or not full_name or not email or not password:
        return jsonify({"message": "Username, full name, email, and password REQUIRED"}), 400

    user_id = db.create_user(username, email, password, role, full_name)
    if not user_id:
        return jsonify({"message": "User already exists or DB error"}), 400
    return jsonify({"message": "User registered successfully"}), 201

# DASHBOARDS
@app.route("/api/admin/dashboard")
@token_required
@role_required("admin")
def admin_dashboard(user_id, role):
    return jsonify({"message": "Welcome Admin", "stats": {"total_users": 120, "active_exams": 5}})

@app.route("/api/student/dashboard")
@token_required
@role_required("student")
def student_dashboard(user_id, role):
    return jsonify({"message": "Welcome Student", "exams": []})

# PROFILE - GET
@app.route("/api/me", methods=["GET"])
@token_required
def get_current_user_profile(user_id, user_role):
    user = db.get_current_user(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "username": user["username"],
        "fullName": user["full_name"],
        "email": user["email"],
        "role": user["role"],
        "phone": user.get("phone", ""),
        "institution": user.get("institution", ""),
        "program": user.get("program", ""),
        "year": user.get("year", ""),
        "last_login": user.get("last_login"),
        "password_changed_at": user.get("password_changed_at")  # ✅ NEW
    })


# PROFILE - UPDATE (Full name + student fields)
@app.route("/api/me", methods=["PUT"])
@token_required
def update_student_profile(user_id, user_role):
    data = request.get_json() or {}
    student_fields = {
        "fullName": data.get("fullName"),
        "phone": data.get("phone"),
        "institution": data.get("institution"),
        "program": data.get("program"),
        "year": data.get("year")
    }
    success = db.update_student_profile(user_id, student_fields)
    if not success:
        return jsonify({"message": "Profile update failed"}), 400
    return jsonify({"message": "Profile updated successfully"}), 200

# PASSWORD CHANGE
@app.route("/api/me/password", methods=["POST"])
@token_required
def change_user_password(user_id, user_role):
    data = request.get_json() or {}
    current = data.get("current_password")
    new = data.get("new_password")
    if not current or not new:
        return jsonify({"message": "Current and new password required"}), 400
    if not db.change_password(user_id, current, new):
        return jsonify({"message": "Invalid current password"}), 400
    return jsonify({"message": "Password changed"}), 200

if __name__ == "__main__":
    app.run(debug=True)

@app.route("/api/student/results", methods=["GET"])
@token_required
def get_student_results(user_id, user_role):
    if user_role != "student":
        return jsonify({"message": "Access denied"}), 403
    
    results = db.get_student_results(user_id)
    stats = db.get_student_stats(user_id)
    
    # Map colors based on status
    for result in results:
        result["color"] = "green" if result["status"] == "Pass" else "red"
        result["date"] = result["completed_at"][:10] if result["completed_at"] else "N/A"
    
    return jsonify({
        "results": results or [],
        "stats": {
            "avgScore": round(stats["avg_score"] or 0, 1),
            "totalExams": stats["total_exams"] or 0,
            "passedExams": stats["passed_count"] or 0
        },
        "message": "No results" if not results else None
    })

@app.route("/api/student/stats", methods=["GET"])
@token_required
def get_student_stats_endpoint(user_id, user_role):
    if user_role != "student":
        return jsonify({"message": "Access denied"}), 403
    
    stats = db.get_student_stats(user_id)
    return jsonify(stats)

@app.route("/api/support/tickets", methods=["POST"])
@token_required
def create_support_ticket(user_id, user_role):
    data = request.get_json()
    if not all(k in data for k in ["type", "subject", "message"]):
        return jsonify({"message": "Missing required fields"}), 400
    
    ticket_id = db.create_support_ticket(user_id, data)
    return jsonify({
        "message": "Ticket created successfully",
        "ticket_id": ticket_id
    }), 201
    
@app.route("/api/support/tickets", methods=["GET"])
@token_required
def get_user_tickets(user_id, user_role):
    tickets = db.get_user_tickets(user_id)
    return jsonify({"tickets": tickets})

@app.route("/api/feedback", methods=["POST"])
@token_required
def submit_feedback(user_id, user_role):
    data = request.get_json()
    required = ["rating", "category", "subject", "message"]
    if not all(k in data for k in required):
        return jsonify({"message": "Missing required fields"}), 400
    
    if data["rating"] < 1 or data["rating"] > 5:
        return jsonify({"message": "Rating must be 1-5"}), 400
    
    feedback_id = db.submit_feedback(user_id, data)
    return jsonify({
        "message": "Feedback submitted successfully!",
        "feedback_id": feedback_id
    }), 201

@app.route("/api/feedback", methods=["GET"])
@token_required
def get_user_feedback(user_id, user_role):
    feedback = db.get_user_feedback(user_id)
    return jsonify({"feedback": feedback})

@app.route("/api/student/dashboard", methods=["GET"])
@token_required
def student_dashboard(user_id, user_role):
    if user_role != "student":
        return jsonify({"message": "Access denied"}), 403
    
    # Get stats (implement these in database.py)
    stats = db.get_student_dashboard_stats(user_id)
    
    return jsonify({
        "enrolled_exams": stats.get("enrolled_exams", 0),
        "upcoming_exams": stats.get("upcoming_exams", 0),
        "notifications": stats.get("notifications", 0)
    })
