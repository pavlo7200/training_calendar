from flask import Flask, render_template, request
from flask import redirect, url_for

app = Flask(__name__)


class Task:
    def __init__(self, title):
        self.title = title
        self.done = False

    def mark_done(self):
        self.done = True


tasks = [Task("Купить тетрадь"), Task("Сделать лабу 3")]


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        title = request.form["title"]
        tasks.append(Task(title))
        return redirect(url_for("index"))
    return render_template("index.html", tasks=tasks)


@app.route("/done/<int:number>", methods=["POST"])
def done(number):
    tasks[number].mark_done()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
