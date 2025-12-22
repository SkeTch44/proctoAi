from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt

from config import Config
from db.database import DatabaseManager
from werkzeug.security import generate_password_hash
from flask_cors import CORS


app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=app.config.get("CORS_ORIGINS", ["http://localhost:3000"]))
db = DatabaseManager(app.config.get("DATABASE_URL", "sqlite:///exam_platform.db"))
db.init_database()


# -----------------------
# HOME
# -----------------------
@app.route("/")
def home():
    return "Backend running"


# -----------------------
# JWT DECORATOR
# -----------------------
def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token or not token.startswith("Bearer "):
            return jsonify({"message": "Token missing"}), 401

        try:
            token = token.split(" ")[1]
            payload = jwt.decode(
                token,
                app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401

        return f(payload["user_id"], payload["role"], *args, **kwargs)

    return wrapper


# -----------------------
# ROLE DECORATOR
# -----------------------
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(user_id, role, *args, **kwargs):
            if role != required_role:
                return jsonify({"message": "Access denied"}), 403
            return f(user_id, role, *args, **kwargs)
        return wrapper
    return decorator


# -----------------------
# AUTH APIs
# -----------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    user = db.authenticate_user(
        data.get("username"),
        data.get("password")
    )

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    token = jwt.encode(
        {
            "user_id": user["id"],
            "role": user["role"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        },
        app.config["JWT_SECRET_KEY"],
        algorithm="HS256"
    )

    return jsonify({"token": token, "user": user})


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "student")

    if not username or not email or not password:
        return jsonify({"message": "All fields required"}), 400

    # Validate role
    if role not in ("student", "teacher", "admin"):
        return jsonify({"message": "Invalid role provided"}), 400

    # Check which field (if any) already exists to give precise feedback
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return jsonify({"message": "Username already exists"}), 400

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already exists"}), 400

    finally:
        conn.close()

    password_hash = generate_password_hash(password)

    user_id = db.create_user(username, email, password_hash, role)

    if not user_id:
        return jsonify({"message": "Failed to create user"}), 500

    return jsonify({"message": "User registered successfully", "user_id": user_id}), 201


# -----------------------
# ROLE-BASED DASHBOARDS
# -----------------------
@app.route("/api/admin/dashboard")
@token_required
@role_required("admin")
def admin_dashboard(user_id, role):
    return jsonify({
        "message": "Welcome Admin",
        "stats": {
            "total_users": 120,
            "active_exams": 5
        }
    })


@app.route("/api/student/dashboard")
@token_required
@role_required("student")
def student_dashboard(user_id, role):
    return jsonify({
        "message": "Welcome Student",
        "exams": []
    })


# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
