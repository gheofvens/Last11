from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init as mig_init, migrate as mig_migrate, upgrade as mig_upgrade
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Явно указываем папки шаблонов и статики
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

# Чиним старый префикс postgres:// -> postgresql://
db_url = os.environ.get("DATABASE_URL", "sqlite:///database.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "supersecretkey123")

db = SQLAlchemy(app)
migrate = Migrate(app, db)

START_DATE = datetime(2025, 4, 10).date()

class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False)

def ensure_migrations():
    """
    Безопасная автогенерация/применение миграций на старте.
    Отключается переменной DISABLE_AUTO_MIGRATE=1
    """
    if os.environ.get("DISABLE_AUTO_MIGRATE") == "1":
        return
    migrations_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
    with app.app_context():
        try:
            needs_init = not os.path.isdir(migrations_dir) or not os.listdir(migrations_dir)
            if needs_init:
                mig_init()
                mig_migrate(message="initial schema")
                mig_upgrade()
            else:
                try:
                    mig_migrate(message="autogen")
                except Exception:
                    pass
                mig_upgrade()
        except Exception as e:
            app.logger.warning(f"Auto-migrate warning: {e}")
            if db_url.startswith("sqlite"):
                db.create_all()

@app.route("/", methods=["GET"])
def index():
    events = Event.query.order_by(Event.date).all()
    today = datetime.today().date()
    days_together = (today - START_DATE).days
    return render_template("index.html", days_together=days_together, events=events, today=today)

@app.route("/add_event", methods=["POST"])
def add_event():
    data = request.get_json() or {}
    name = data.get("name")
    date_str = data.get("date")
    if name and date_str:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        new_event = Event(name=name, date=date)
        db.session.add(new_event)
        db.session.commit()
        return jsonify({"success": True, "id": new_event.id})
    return jsonify({"success": False}), 400

@app.route("/about")
def about():
    return render_template("about.html")

# запускаем автоприменение миграций
ensure_migrations()

if __name__ == "__main__":
    # локально: waitress не нужен, просто запустить
    app.run(debug=True)
