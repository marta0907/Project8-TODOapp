import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
ckeditor = CKEditor(app)
app.config["CKEDITOR_ENABLE_CSRF"]=False
Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view='login'

class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)

db.init_app(app)

class User(db.Model, UserMixin):
    __tablename__= "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    
    lists = relationship("List", back_populates="user")

class List(db.Model):
    __tablename__ = "lists"
    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(String(200), nullable=False)
    created_at = mapped_column(db.DateTime, default=datetime.datetime.now)
    user_id = mapped_column(Integer, db.ForeignKey('users.id'), nullable=False)

    user = relationship("User", back_populates="lists")
    tasks = relationship("Task", back_populates="list", cascade="all, delete-orphan")
    def is_done(self):
        return all(task.status == 'Done' for task in self.tasks)
    def task_completed(self):
        total_tasks = len(self.tasks)
        completed_tasks =sum(1 for task in self.tasks if task.status == 'Done')
        return f"{completed_tasks}/{total_tasks}" if total_tasks else "0/0"

class Task(db.Model):
    __tablename__ = "tasks"
    id = mapped_column(Integer, primary_key=True)
    content = mapped_column(String(500), nullable=False)
    status = mapped_column(String(50), default='Not Started')
    list_id = mapped_column(Integer, db.ForeignKey('lists.id'), nullable=False)

    list = relationship("List", back_populates="tasks")

with app.app_context():
    db.create_all()
    
@login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        return None
    try:
        return User.query.get(int(user_id))
    except ValueError:
        return None


# hash the user's password when creating a new user with werkzeug
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if request.method == "POST":
        if form.validate_on_submit():
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already exists', 'error')
                return redirect(url_for('register'))
            else:
                hashed_password = generate_password_hash(request.form.get("password"), method='pbkdf2', salt_length=8)
                new_user = User(name=form.name.data, email=form.email.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful", "success")
            # login_user(new_user) - if one wants the user to be logged in directly after registration, then user can be redirected to lists.html
            return redirect(url_for("login", logged_in=False))
    return render_template("register.html", form=form)

# Retrieve a user from the database based on their email.
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            new_user = db.session.execute(db.select(User).where(User.email == email)).scalar()
            login_user(user)
            flash("Logged in successfully", "success")
            return redirect(url_for('lists', user=new_user, logged_in=True))
        else:
            flash("Invalid password", "danger")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home', logged_id=False))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/lists')
@login_required
def lists():
    user_lists = List.query.filter_by(user_id=current_user.id).all()
    
    count_lists=len(user_lists)
    completed_lists=sum(1 for lis in user_lists if lis.is_done())
    grouped_lists = {}
    for lis in user_lists:
        month_year=lis.created_at.strftime("%B %Y")
        if month_year not in grouped_lists:
            grouped_lists[month_year]=[]
        grouped_lists[month_year].append(lis)
    
    for month_year in grouped_lists:
        grouped_lists[month_year]=sorted(grouped_lists[month_year], key=lambda x: x.is_done(), reverse=False)
    return render_template('lists.html', all_lists=user_lists, user_name=current_user.name, grouped_lists=grouped_lists, number_of_lists=count_lists, completed_lists=completed_lists)
    
@app.route('/lists/create', methods=["GET", "POST"])
@login_required
def create_list():
    if request.method == "POST":
        
        list_title = request.form.get('title')
        new_list = List(title=list_title, user_id=current_user.id)
        db.session.add(new_list)
        db.session.commit()
        
        task_names=request.form.getlist('task-name[]')
        
        for name in task_names:
            if name.strip():
                task = Task(content=name, status="Not Started", list_id=new_list.id)
                db.session.add(task)
            
        db.session.commit()
        flash('List created successfully!', 'success')
        return redirect(url_for('lists'))
    date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template('create_list.html', date=date, user_name=current_user.name)

@app.route('/lists/delete/<int:list_id>', methods=["POST"])
@login_required
def delete_list(list_id):
    try:
        list_to_delete = List.query.filter_by(id=list_id, user_id=current_user.id).first()

        if list_to_delete:
            db.session.delete(list_to_delete)
            db.session.commit()
            flash("List deleted successfully!", "success")
        else:
            flash("List not found or you don't have permission to delete it.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting list: {str(e)}", "danger")
    finally:
        db.session.close()
    return redirect(url_for('lists'))


@app.route('/view_list/<int:list_id>', methods=['GET', 'POST'])
@login_required
def view_list(list_id):
    todo_list = List.query.filter_by(id=list_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        for task in todo_list.tasks:
            new_status = request.form.get(f"status_{task.id}")
            if new_status:
                task.status = new_status
            if f"task_done_{task.id}" in request.form:
                task.status = 'Done'

        db.session.commit()
        flash('List updated successfully!', 'success')
        return redirect(url_for('lists'))

    return render_template('view_list.html', todo_list=todo_list, user_name=current_user.name)


if __name__ == '__main__':
    app.run(debug=True)