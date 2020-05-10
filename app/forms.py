from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email


class RegisterForm(FlaskForm):
    '''
    Form to register a new user of the system
    '''
    email = StringField('Email', [
        Email(message='Not a valid email address.'),
        DataRequired()],
        render_kw={'placeholder': 'Email'})
    kindle_email = StringField('Kindle Email', [
        Email(message='Not a valid email address.'),
        DataRequired()],
        render_kw={'placeholder': 'Kindle email'})
    submit = SubmitField('Register')
    
    
class ReportArticleForm(FlaskForm):
    '''
    Form to send reports fo bad articles
    '''
    comment = StringField('Comments',
        render_kw={'placeholder': 'Comments'}
    )
    email = HiddenField()
    url = HiddenField()
    submit = SubmitField('Send Report')