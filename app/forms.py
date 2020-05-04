from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email


class RegisterForm(FlaskForm):
    '''Register Form'''
    email = StringField('Email', [
        Email(message=('Not a valid email address.')),
        DataRequired()])
    kindle_email = StringField('Kindle Email', [
        Email(message=('Not a valid email address.')),
        DataRequired()])
    submit = SubmitField('Submit')