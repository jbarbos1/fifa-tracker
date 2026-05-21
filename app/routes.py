from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import LeagueMember, League
from functools import wraps
from app.forms import RegistrationForm, LoginForms, LeagueCreateForm
from app.db_manager import DBManager

main = Blueprint('main', __name__)


def get_current_member():
    """Return the logged-in LeagueMember or None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return LeagueMember.query.get(user_id)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in first', 'Warning')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)

    return decorated


@main.route('/')  # Create route for homepage
def home():
    return render_template('home.html')  # Will show html template home


@main.route('/about')
def about():
    return render_template('about.html')


# --------------
# Login
# --------------
@main.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to dash
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    form = LoginForms()

    if form.validate_on_submit():
        identifier = form.identifier.data.strip()
        password = form.password.data
        # Query db for uname or email
        member = (
                LeagueMember.query.filter_by(username=identifier).first()
                or LeagueMember.query.filter_by(email=identifier.lower()).first()
        )

        # Validating password and prevent user-enumeration
        if member and check_password_hash(member.password_hash, password):
            # Regenerate session ID to prevent session fixation
            session['user_id'] = member.id
            flash(f"Welcome back, {member.username}!", 'success')
            return redirect(url_for('main.dashboard'))
        # Generic error message avoid disclosing which account exist
        flash('Invalid credentials. Please try again.', 'error')
        return redirect(url_for('main.login'))
    return render_template('login.html', form=form)


@main.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))


# -------------
# Registration
# -------------
@main.route('/register', methods=["GET", "POST"])
def register():
    form = RegistrationForm()

    # Triggers only when user slicks submit and data is valid
    if form.validate_on_submit():

        def create_user_transaction(db_session):
            email = form.email.data.strip().lower()
            password = form.password.data

            username = form.username.data.strip() if form.username.data else email.split('@')[0]

            new_user = LeagueMember(
                email=email,
                username=username,
                password_hash=generate_password_hash(password),
                league_id=None  # Does python already do this once you create instance
            )

            db_session.add(new_user)
            db_session.flush()
            return (new_user)

        # db.session.flush()  # gives new_user its primary key before commit
        success, result = DBManager.execute_transaction(create_user_transaction)
        if success:
            session['user_id'] = result.id
            flash('Account created successfully', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash(f"Registration failed: Database error occurred.")
            return redirect(url_for('main.login'))
    # Triggers if the user submitted invalid data
    elif request.method == 'POST':
        flash('Invalid form submission', 'error')
    return render_template('register.html', form=form)


# --------------------
# Logged in template
# --------------------
# Dashboard
# ---------------------
@main.route('/dashboard')
@login_required
def dashboard():
    member = get_current_member()
    return render_template('dashboard.html', member=member)


# -------------------
# League (Create/find/search)
# -------------------

@main.route('/league/create', methods=['GET', 'POST'])
@login_required
def create_league():
    member = get_current_member()

    # Check if they already have league
    if member.league_id is not None:
        flash('You may not create league while in league. Must leave current league.')
        return redirect(url_for('main.dashboard'))  # may need to change link
    form = LeagueCreateForm()

    # validate on submit handles both checking for POST and running all validators
    if form.validate_on_submit():

        def create_league_transaction(db_session):
            league = League(name=form.name.data.strip())
            db_session.add(league)
            db_session.flush()
            member.league_id = league.id

            return league

        success, result = DBManager.execute_transaction(create_league_transaction)
        if success:
            flash(f"League {result.name} created and you were added.", 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Unexpected error occurred. Try again later.', 'error')
            return redirect(url_for('main.dashboard'))
    return render_template('create_league.html', member=member, form=form)


@main.route("/league/find")
@login_required
def find_league():
    """Show all leagues the current member is NOT already in."""
    member = get_current_member()
    leagues = League.query.filter(League.id != member.league_id).all() if member.league_id else League.query.all()
    return render_template("find_league.html", leagues=leagues, member=member)


@main.route("/league/search")
@login_required
def search_league():
    member = get_current_member()
    query = request.args.get("q", "").strip()

    # 1. Start with a base query that excludes the user's current league
    # (Just like your /find logic)
    base_query = League.query
    if member.league_id:
        base_query = base_query.filter(League.id != member.league_id)

    # 2. Apply the search filter only if a query exists
    if query:
        leagues = base_query.filter(League.name.ilike(f"%{query}%")).all()
    else:
        leagues = base_query.all()

    # If this is purely for AJAX, you might eventually point this to a
    # template that ONLY contains the list items, rather than a full page.
    return render_template("search_league.html", leagues=leagues, query=query, member=member)


@main.route("/league/join/<uuid:league_id>", methods=["POST"])
@login_required
def join_league(league_id):
    member = get_current_member()
    league = League.query.get_or_404(league_id)

    if member.league_id == league.id:
        flash("You are already in this league.", "info")
        return redirect(url_for("main.find_league"))

    def join_league_transaction(db_session):
        member.league_id = league.id
        return member

    success, result = DBManager.execute_transaction(join_league_transaction)
    if success:
        # member.league_id = league.id
        # db.session.commit()
        flash(f'You joined "{league.name}"!', "success")
    else:
        flash('An unexpected error occurred. Try again later', 'error')
    return redirect(url_for("main.dashboard"))


@main.route("/league/leave", methods=["POST"])
@login_required
def leave_league():
    member = get_current_member()
    if member.league_id:
        def leave_league_transaction(db_session):
            member.league_id = None
            return member

        success, result = DBManager.execute_transaction(leave_league_transaction)
        if success:
            flash("You have left your league.", "info")
    return redirect(url_for("main.dashboard"))


# ──────────────────────────────────────────
# Manage team (stub — extend as needed)
# ──────────────────────────────────────────

@main.route("/team/manage")
@login_required
def manage_team():
    member = get_current_member()
    return render_template("manage_team.html", member=member)
