from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import LeagueMember, League


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message='Please enter a valid email address. ')])
    username = StringField('Username')
    password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords do not match.')
    ])

    # WTForms automatically runs methods starting with 'validate_' IKR WTF
    def validate_email(self, email):
        normalized_email = email.data.strip().lower()
        member = LeagueMember.query.filter_by(email=normalized_email).first()
        if member:
            raise ValidationError('An account with thta email already exists')  # Throw

    def validate_username(self, username):
        if username and username.data:
            member = LeagueMember.query.filter_by(username=username.data.strip()).first()
            if member:
                raise ValidationError('That username is already taken')


class LoginForms(FlaskForm):
    identifier = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class LeagueCreateForm(FlaskForm):
    name = StringField(
        'League Name',
        validators=[
            DataRequired(message='League name is required. '),
            Length(max=120, message='Name cannot exceed 120 characters.')
        ]
    )

    submit = SubmitField('Create Leaue')

    def validate_name(self, name):
        existing_league = League.query.filter_by(name=name.data.strip().first())
        if existing_league:
            raise ValidationError('League with that name exists already.')
