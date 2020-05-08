from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email


class RegisterForm(FlaskForm):
    """
    Form to register a new user of the system
    """
    email = StringField('Email', [
        Email(message='Not a valid email address.'),
        DataRequired()],
        render_kw={"placeholder": "Email"})
    kindle_email = StringField('Kindle Email', [
        Email(message='Not a valid email address.'),
        DataRequired()],
        render_kw={"placeholder": "Kindle email"})
    submit = SubmitField('Register')