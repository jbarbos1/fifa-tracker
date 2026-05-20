from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from app import db
from app.models import LeagueMember


main = Blueprint('main', __name__)


@main.route('/')  # Create route for homepage
def home():
    return render_template('home.html')  # Will show html template home


@main.route('/about')
def about():
    return render_template('about.html')


@main.route('/login')
def login():
    return render_template('login.html')


@main.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not email:
            flash('Email is required.', 'error')  # review syntax of flash
            return redirect(url_for('main.register'))  # Why is main referenced when it is blueprint

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('main.register'))

        if LeagueMember.query.filter_by(email=email).first():
            flash('Email is already registered.', 'error')
            return redirect(url_for('main.register'))

        if username:
            existing_username = LeagueMember.query.filter_by(username=username).first()
            if existing_username:
                flash('Username is already taken.', 'error')
                return redirect(url_for('main.register'))

        password_hash = generate_password_hash(password)

        new_user = LeagueMember(
            email=email,
            username=username if username else 'temp_username',
            password_hash=password_hash,
            league_id=None
        )

        db.session.add(new_user)
        db.session.flush()  # gives new_user its primary key before commit

        if not username:
            email_prefix = email.split('@')[0]
            generated_username = f'{email_prefix}_{new_user.id}'
            new_user.username = generated_username
        try:
            db.session.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            print(e) #debugging
            flash('An unexpected error occurred', 'error')
        finally:
            return redirect(url_for('main.login'))

    return render_template('register.html')
