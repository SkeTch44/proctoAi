from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150),unique=True, nullable=False)
    email = db.Column(db.String(144),unique=True, nullable=False)
    password = db.Column(db.Text(48), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='viewer')

    def __repr__(self):
        return f'<User {self.username}>'
