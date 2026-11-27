from datetime import date
import calendar
from flask import render_template, request
from flask import redirect, url_for

from flask_login import login_user, logout_user
from flask_login import login_required, current_user
# куча импортов которые нельзя трогать никому, только добавлять


from config import app, db
from models import User, Train, TrainList, Comment


@app.route("/register", methods=["GET", "POST"])
def register():  # функция регистрации пользователя
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("user_type") or "client"

        if not username or not password:
            error = "Введите логин и пароль"
        elif db.session.scalar(
                db.select(User).filter_by(username=username)) is not None:
            error = "Этот логин уже занят"
        else:
            user = User(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        query = db.select(User).filter_by(username=username)
        user = db.session.scalar(query)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        error = "Неверный логин или пароль"
        return render_template("login.html", error=error)
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("login"))


MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


@app.route("/")
@login_required
def index():  # календарь
    today = date.today()
    year = request.args.get("year", default=today.year, type=int)
    month = request.args.get("month", default=today.month, type=int)
    selected_date = request.args.get("date")
    weeks = calendar.monthcalendar(year, month)

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

    # имена пользователей, чтобы тренер видел, чья тренировка
    usernames = {}
    for u in db.session.scalars(db.select(User)).all():
        usernames[u.id] = u.username

    events = {}
    for e in rows:
        events.setdefault(e.day, []).append(
            (e.time, e.title, e.id, usernames.get(e.user_id, "—"))
        )

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
        is_trainer=(current_user.role == "trainer"),
    )


@app.route("/add_training_day", methods=["POST"])  # добавление события в календарь
@login_required
def add_event():
    date_str = request.form.get("date")
    time_str = request.form.get("time")
    title = (request.form.get("title") or "").strip()

    if not date_str or not time_str or not title:
        return "Время и название события обязательны", 400

    try:
        d, m, y = map(int, date_str.split("."))
    except ValueError:
        return "Некорректная дата", 400

    db.session.add(Train(year=y, month=m, day=d, time=time_str, title=title, user_id=current_user.id))
    db.session.commit()

    return redirect(url_for("index", year=y, month=m))


@app.route("/delete", methods=["POST"])  # удаление записи в календаре
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

    if event.user_id != current_user.id:  # удаляет только владелец
        return "Можно удалять только свои тренировки"
    y, m = event.year, event.month
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for("index", year=y, month=m))


@app.route("/train/<int:train_id>")
@login_required
def train_page(train_id):  # страница конкретной тренировки
    train = db.session.get(Train, train_id)
    user=db.session.get(User, train.user_id)
    if not train:
        return "Тренировка не найдена", 404

    if current_user.role != "trainer" and train.user_id != current_user.id:
        return "Нет доступа к этой тренировке", 403

    exercises = db.session.scalars(
        db.select(TrainList).filter_by(train_id=train.id).order_by(TrainList.id)
    ).all()
    comments = db.session.scalars(
        db.select(Comment).filter_by(train_id=train.id).order_by(Comment.created_at)
    ).all()

    return render_template(
        "training_list.html",
        train=train,
        user=user,
        exercises=exercises,
        comments=comments,
        is_owner=(train.user_id == current_user.id),
        is_trainer=(current_user.role == "trainer"),
    )


@app.route("/add_training", methods=["POST"])  # добавляет упражнение в тренировку
@login_required
def add_training():
    train_id_str = request.form.get("train_id")
    name_of_exercise = (request.form.get("name_of_exercise") or "").strip()
    sets_str = request.form.get("sets")
    reps_str = request.form.get("reps")
    kg_str = request.form.get("kg")

    if not train_id_str or not name_of_exercise or not sets_str or not reps_str or not kg_str:
        return "Нет данных об упражнении", 400

    train = db.session.get(Train, int(train_id_str))
    if not train:
        return "Тренировка не найдена", 404
    if current_user.role != "trainer" and train.user_id != current_user.id:
        return "Это не ваша тренировка", 403

    try:
        sets = int(sets_str)
        reps = int(reps_str)
        kg = int(kg_str)
    except ValueError:
        return "Подходы, повторения и вес должны быть числами", 400

    if sets <= 0 or reps <= 0 or kg <= 0:
        return "Числа должны быть больше нуля", 400

    db.session.add(TrainList(
        name_of_exercise=name_of_exercise,
        sets=sets,
        reps=reps,
        kg=kg,
        train_id=train.id,
        user_id=current_user.id,
    ))
    db.session.commit()

    return redirect(url_for("train_page", train_id=train.id))


@app.route("/delete_exercise", methods=["POST"])  # удаление упражнения
@login_required
def delete_exercise():
    exercise_id = request.form.get("exercise_id")

    if not exercise_id:
        return "Не указан ID упражнения", 400

    try:
        exercise_id = int(exercise_id)
    except ValueError:
        return "Некорректный ID", 400

    exercise = db.session.get(TrainList, exercise_id)

    if not exercise:
        return "Упражнение не найдено", 404
    if exercise.train.user_id != current_user.id:  # можно удалять только из своей тренировки
        return "Можно удалять только из своей тренировки", 403

    train_id = exercise.train_id
    db.session.delete(exercise)
    db.session.commit()

    return redirect(url_for("train_page", train_id=train_id))


@app.route("/add_comment", methods=["POST"])  # комментарий тренера к тренировке
@login_required
def add_comment():
    if current_user.role != "trainer":
        return "Комментировать может только тренер", 403

    train_id = request.form.get("train_id")
    text = (request.form.get("text") or "").strip()
    if not train_id or not text:
        return "Нужен ID тренировки и текст комментария", 400

    train = db.session.get(Train, int(train_id))
    if not train:
        return "Тренировка не найдена", 404

    db.session.add(Comment(train_id=train.id, author_id=current_user.id, text=text))
    db.session.commit()
    return redirect(url_for("train_page", train_id=train.id))
