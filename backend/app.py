# The app.py - controlling the main backend for the RBAC model implementation
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from backend.extensions import db, User
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['FLASK_SECRET_KEY'] = 'secret' 
app.config['FLASK_SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager= LoginManager()
login_manager.login_view= 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 
