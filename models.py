from pathlib import Path
from datetime import date, datetime
import calendar
from flask import Flask, render_template, request
from flask import redirect, url_for
from flask_login import LoginManager, UserMixin
from flask_login import login_user, logout_user
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash  # куча импортов которые нельзя трогать никому, только добавлять


from config import app,db,login_manager


class User(UserMixin, db.Model):  # создает нашего пользователя с характеристиками
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default="client")  # разделение доступа

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Train(db.Model):  # тренировка = событие в календаре
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    time = db.Column(db.String(5), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # кто создал (клиент)

    exercises = db.relationship("TrainList", backref="train",
                                cascade="all, delete-orphan")  # при удалении тренировки удалятся упражнения
    comments = db.relationship("Comment", backref="train",
                               cascade="all, delete-orphan")  # и комментарии тоже


class TrainList(db.Model):  # упражнения конкретной тренировки
    id = db.Column(db.Integer, primary_key=True)
    name_of_exercise = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer, nullable=False)  # подходы
    reps = db.Column(db.Integer, nullable=False)  # повторения
    kg = db.Column(db.Integer, nullable=False)  # вес
    train_id = db.Column(db.Integer, db.ForeignKey("train.id"), nullable=False)  # к какой тренировке относится
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # чья тренировка


class Comment(db.Model):  # комментарий тренера к тренировке
    id = db.Column(db.Integer, primary_key=True)
    train_id = db.Column(db.Integer, db.ForeignKey("train.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    author = db.relationship("User", backref="comments")  # чтобы выводить имя автора

with app.app_context():
        db.create_all()

@login_manager.user_loader
def load_user(user_id):  # позволяет совершать быстрый вход
    return db.session.get(User, int(user_id))
