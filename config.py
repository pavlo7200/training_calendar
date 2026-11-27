from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
  # куча импортов которые нельзя трогать никому, только добавлять

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "train.db"  # создает train.db это наша таблица с данными, иногда нам
# придется ее удалять для обновления данных но эту часть тоже не трогаем

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_ECHO"] = True
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
