from pathlib import Path
from datetime import date
import calendar
from flask import Flask, render_template, request
from flask import redirect, url_for
from flask_login import LoginManager, UserMixin
from flask_login import login_user, logout_user
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash #куча импортов которые нельзя трогать никому, только добавлять

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "train.db" #создает train.db это наша таблица с данными, иногда нам
# придется ее удалять для обновления данных но эту часть тоже не трогаем

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_ECHO"] = True
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
#с этим я не разобрался но это базовая база поэтому тоже не трогаем

class User(UserMixin, db.Model): #создает нашего пользователя с характеристиками
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default="client") #это начало нашего разделения доступа


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) #пароли я скопировал из презентации, так что
    # тут делать нечего


class Train(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    time = db.Column(db.String(5))
    title = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id")) #это надо будет сильно менять так как
# пока что этот класс чисто для календаря, признаю я это вайбкодил, но примерно понимаю что как



@login_manager.user_loader
def load_user(user_id): #связана со следующей функцией, она позволяет
    return db.session.get(User, int(user_id))


@app.route("/register", methods=["GET", "POST"])
def register(): # функция регистрации пользователя
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("user_type") or "client"

        if not username or not password:
            error = "Введите логин и пароль"
        elif db.session.scalar( db.select(User).filter_by(username=username) ) is not None:
            error = "Этот логин уже занят"
        else:
            user = User(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)# вход сразу после регистрации, сильно необходимая вещь, которую я плохо понял, но обещаю исправиться
            return redirect(url_for("index"))

    return render_template("register.html", error=error)
#в этой функции важно все, но возможно будем что-то менять

@app.route("/login", methods=["GET", "POST"])
def login():#стандартный вход из презентации
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        query = db.select(User).filter_by(username=username)
        user = db.session.scalar(query)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        error = "Неверный логин или пароль"
        return render_template("login.html", error=error)
    return render_template("login.html")



@app.route("/logout", methods=["POST"])
def logout(): # стандартный выход из аккаунта, возможно поменяем только html
    logout_user()
    return redirect(url_for("login"))

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
# эти списки необходимы для работы календаря в html, пока что плохо понимаю в html
# но чуть позже разберусь

@app.route("/")
@login_required
def index(): #это основа нашего проекта пока что, тут календарь, он еще не совсем интерактивный, но что есть
    today = date.today()
    year = request.args.get("year", default=today.year, type=int)
    month = request.args.get("month", default=today.month, type=int)
    selected_date = request.args.get("date")
    # сетка месяца:
    weeks = calendar.monthcalendar(year, month)

    # события месяца из базы: {день: [(время, название), ...]}
    if current_user.role == "trainer":
        # тренер видит все события за месяц
        rows = (Train.query
                .filter_by(year=year, month=month)
                .order_by(Train.day, Train.time)
                .all())
    else:
        # клиент видит только свои события
        rows = (Train.query
                .filter_by(user_id=current_user.id, year=year, month=month)
                .order_by(Train.day, Train.time)
                .all())
    events = {}
    for e in rows:
        events.setdefault(e.day, []).append((e.time, e.title, e.id))

    # соседние месяцы для стрелок навигации
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)


    return render_template(
        "calendar.html",
        weeks=weeks,
        year=year,
        month=month,
        month_name=MONTHS[month - 1],
        weekdays=WEEKDAYS,
        prev=(prev_y, prev_m),
        next=(next_y, next_m),
        events=events,
        today=today,
        selected_date=selected_date,
    )

@app.route("/add", methods=["POST"])
@login_required
def add_event():
    date_str = request.form.get("date")
    time_str = request.form.get("time") or None
    title = (request.form.get("title") or "").strip()

    if not time_str or not title:
        return "Время и название события обязательны", 400

    d, m, y = map(int, date_str.split("."))

    db.session.add(Train(year=y, month=m, day=d, time=time_str, title=title, user_id=current_user.id))
    db.session.commit()

    return redirect(url_for("index", year=y, month=m))

@app.route("/delete", methods=["POST"])
@login_required
def delete_event():
    event_id = request.form.get("event_id")

    if not event_id:
        return "Не указан ID события", 400

    try:
        event_id = int(event_id)
    except ValueError:
        return "Некорректный ID", 400

    event = db.session.get(Train, event_id)

    if not event:
        return "Событие не найдено", 404




    db.session.delete(event)
    db.session.commit()

    return redirect(url_for("index", year=event.year, month=event.month))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)


