from flask import Flask, render_template, request, redirect, url_for, session, flash  # Импортируем flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)  # Используйте __name__
app.secret_key = 'REPLACE_WITH_YOUR_SECRET_KEY'  # Замените на что-то уникальное и сложное
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(50), unique=True, nullable=False)
    buttons = db.relationship('Button', backref='schedule', lazy=True)

class Button(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    particulars = db.Column(db.String(152), nullable=True)
    participant = db.Column(db.String(152), nullable=True)
    color = db.Column(db.String(20), nullable=False)

with app.app_context():
    db.create_all()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return "Пользователь с таким именем уже существует", 400

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash("Вы успешно вошли!", 'success')  # Используем flash
            return redirect(url_for('home'))

        flash("Неверные имя пользователя или пароль", 'error')  # Используем flash

    return render_template('login.html')

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))  # Если пользователь авторизован
    else:
        return redirect(url_for('login'))  # Если пользователь не авторизован

@app.route('/home')
@login_required
def home():
    error = request.args.get('error')
    return render_template('home.html', error=error)

@app.route('/create_schedule', methods=['POST'])
@login_required  # Добавьте декоратор для защиты маршрута
def create_schedule():
    new_password = request.form['new_password']
    existing_schedule = Schedule.query.filter_by(password=new_password).first()
    if existing_schedule:
        return redirect(url_for('home', error="Этот пароль уже используется."))

    new_schedule = Schedule(password=new_password)
    db.session.add(new_schedule)
    db.session.commit()
    return redirect(url_for('edit_schedule', schedule_id=new_schedule.id))

@app.route('/view_schedule', methods=['POST'])
def view_schedule():
    password = request.form['password']
    schedule = Schedule.query.filter_by(password=password).first()
    if not schedule:
        return redirect(url_for('home', error="Этот пароль еще не используется."))

    return redirect(url_for('edit_schedule', schedule_id=schedule.id))

@app.route('/edit_schedule/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(schedule_id):
    schedule = Schedule.query.get(schedule_id)
    if request.method == 'POST':
        particulars = request.form.get('particulars')
        participant = request.form.get('participant')
        color = 'lightgreen' if not participant else 'pink'

        if color and particulars:
            new_button = Button(schedule_id=schedule.id, particulars=particulars, participant=participant, color=color)
            db.session.add(new_button)
            db.session.commit()
            return redirect(url_for('edit_schedule', schedule_id=schedule.id))

        return redirect(url_for('edit_schedule', schedule_id=schedule.id))

    buttons = Button.query.filter_by(schedule_id=schedule.id).all()
    return render_template('schedule.html', schedule=schedule, buttons=buttons)

@app.route('/edit_button/<int:button_id>', methods=['GET', 'POST'])
@login_required  # Добавьте декоратор для защиты маршрута
def edit_button(button_id):
    button = Button.query.get(button_id)

    if request.method == 'POST':
        particulars = request.form.get('particulars')
        participant = request.form.get('participant')

        if not particulars:
            return redirect(url_for('edit_schedule', schedule_id=button.schedule_id))

        color = 'lightgreen' if not participant else 'pink'

        button.particulars = particulars
        button.participant = participant
        button.color = color

        db.session.commit()
        return redirect(url_for('edit_schedule', schedule_id=button.schedule_id))

    return render_template('edit_button.html', button=button)

@app.route('/save_password/<int:schedule_id>', methods=['POST'])
@login_required  # Добавьте декоратор для защиты маршрута
def save_password(schedule_id):
    password = request.form['password']
    schedule = Schedule.query.get(schedule_id)
    schedule.password = password
    db.session.commit()
    return redirect(url_for('edit_schedule', schedule_id=schedule.id))

@app.route('/delete_button/<int:button_id>', methods=['POST'])
@login_required  # Добавьте декоратор для защиты маршрута
def delete_button(button_id):
    button = Button.query.get(button_id)
    if button:
        schedule_id = button.schedule_id
        db.session.delete(button)
        db.session.commit()
        return redirect(url_for('edit_schedule', schedule_id=schedule_id))
    return redirect(url_for('home'))

@app.route('/delete_schedule/<int:schedule_id>', methods=['POST'])
@login_required  # Добавьте декоратор для защиты маршрута
def delete_schedule(schedule_id):
    schedule = Schedule.query.get(schedule_id)
    if schedule:
        buttons = Button.query.filter_by(schedule_id=schedule_id).all()
        for button in buttons:
            db.session.delete(button)
        db.session.delete(schedule)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)