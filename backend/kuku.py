# kuku.py  (extra full-stack logic + same server instance)

from datetime import datetime
import json
import sqlite3

from flask import jsonify, request
from functools import wraps

# Import the existing app + socketio from app.py
from .app import app, socketio, init_db, token_required

DB_PATH = "exam_platform.db"


# Example: role-based decorator on top of token_required
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(user_id, user_role, *args, **kwargs):
            if user_role != required_role:
                return jsonify({"message": "Access denied"}), 403
            return f(user_id, user_role, *args, **kwargs)
        return wrapper
    return decorator


# Example: student dashboard (separate from admin dashboard in app.py)
@app.route("/api/student/dashboard", methods=["GET"])
@token_required
@role_required("student")
def student_dashboard(user_id, user_role):
    # You can load dynamic data here later
    return jsonify({
        "message": "Welcome Student",
        "exams": []
    })


# Optional: extra permissions endpoint (if you did not already define it)
@app.route("/api/submit_permissions", methods=["POST"])
@token_required
def submit_permissions(user_id, user_role):
    data = request.get_json() or {}
    session_id = data.get("session_id")
    permissions = data.get("permissions")

    if not permissions:
        return jsonify({"message": "Permissions payload required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            user_id INTEGER,
            permissions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()

    cursor.execute(
        "INSERT INTO student_permissions (session_id, user_id, permissions) VALUES (?, ?, ?)",
        (session_id, user_id, json.dumps(permissions)),
    )
    conn.commit()
    conn.close()

    socketio.emit(
        "permission_update",
        {
            "session_id": session_id,
            "user_id": user_id,
            "permissions": permissions,
            "timestamp": datetime.now().isoformat(),
        },
        room=f"session_{session_id}" if session_id else None,
    )

    return jsonify({"message": "Permissions saved successfully"})


# Any other extra routes / experimental APIs go here.


if __name__ == "__main__":
    # Ensure DB is ready, then reuse the same SocketIO server
    init_db()
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
