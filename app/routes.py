import requests
import smtplib
import ssl
import configparser
import os

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import request
from flask import jsonify
from flask import render_template
from flask import url_for
from flask import redirect
from uuid import uuid4
from rq.job import Job
from worker import conn
from requests.exceptions import RequestException
from EmailWebpage.EmailWebpage import EmailWebpage

from app import app
from app import db
from app import q
from app.models import User
from app.forms import RegisterForm
from app.extensions import csrf
from app.config import BASE_DIR

'''
__author__ = "Phil Nicholls"
__copyright__ = "Copyright 2020, Phil Nicholls"
__credits__ = ["Phil Nicholls"]
__license__ = "GNUv3"
__version__ = "0.1.0"
__maintainer__ = "Phil Nicholls"
__email__ = "phil.j.nicholls@gmail.com"
__status__ = "Development"
__tests__ = ["pep8", "todo"]

Takes a URL, beautifies the content and sends it on to
a Kindle for easy reading on the eyes.

Runs as a Flask REST API on a web server of your choice
'''


@app.errorhandler(Exception)
def handle_error(error):
    """
    Catches errors from the app and tries to send back
    a nice HTTP header and JSON response
    :param error: The error that has been raised
    :return:
    """
    message = [str(x) for x in error.args]

    status_code = None
    try:
        status_code = str(int(error.strerror))
    except:
        # Maybe strerror is not what I thought
        status_code = '500'

    if not status_code:
        status_code = '500'

    success = False
    response = {
        'success': success,
        'error': {
            'type': error.__class__.__name__,
            'message': message,
        }
    }

    return jsonify(response), status_code


def send_email(to_email,
               subject,
               html=None,
               plain_text=None):
    """
    Sends an email using redentials from the .sendtokindle.rc file
    :param to_email: Recipient
    :param subject: Email subject
    :param html: HTML body for the email
    :param plain_text: Plain text body for the email
    :return:
    """

    config = get_config()

    sender_email = config['SMTP']['EMAIL']
    if 'USERNAME' in config['SMTP']:
        username = config['SMTP']['USERNAME']
    else:
        username = sender_email
    password = config['SMTP']['PASSWORD']
    host = config['SMTP']['HOST']
    port = config['SMTP']['PORT']

    message = MIMEMultipart("alternative")

    if plain_text:
        part1 = MIMEText(plain_text, "plain")
        message.attach(part1)
    if html:
        part2 = MIMEText(html, "html")
        message.attach(part2)

    message["Subject"] = subject
    message["From"] = f'Send To Kindle <{sender_email}>'
    message["To"] = to_email

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(username, password)
        server.sendmail(
            sender_email, to_email, message.as_string()
        )
        server.quit()


def get_config():
    if os.path.exists(os.path.join(BASE_DIR, '.sendtokindle.rc')):
        config = configparser.ConfigParser()
        config.read(os.path.join(BASE_DIR, '.sendtokindle.rc'))
        return config
    else:
        raise RequestException('Missing server config.', 404)


def process_and_send_page(email, url):
    config = get_config()

    send_page = EmailWebpage(email=email,
                             url=url,
                             smtp_host=config['SMTP']['HOST'],
                             smtp_user=config['SMTP']['USERNAME'],
                             smtp_password=config['SMTP']['PASSWORD'],
                             smtp_port=config['SMTP']['PORT'],
                             smtp_email=config['SMTP']['EMAIL'],
                             kindlegen_path=os.path.join(BASE_DIR, 'kindlegen'))
    send_page.send()

@app.route('/api', methods=['POST'])
@csrf.exempt
def send_page_to_kindle():
    """
    Public api which takes a token and url, finds the main page content
    and emails it as a mobi file.
    :return:
    """

    # If no URL is specified, raise an errorException
    if 'url' not in request.values:
        raise RequestException('Missing parameter "url".', 400)

    if 'token' not in request.values:
        raise RequestException('Missing parameter "token".', 400)

    user = User.query.filter_by(api_token=request.values['token']).first()

    if not user:
        raise RequestException('No matching token found.', 401)

    if not user.verified:
        raise RequestException('You have not verified your email adress.', 401)

    job = q.enqueue_call(
        func = process_and_send_page, args = (user.kindle_email, request.values['url']), result_ttl = 5000
    )

    return {'success': True}, 200


@app.route('/verify', methods=['GET'])
def verify():
    """
    Verify email ownership with email_token
    :return: Response confirming verification or RequestException
    """
    user = User.query.filter_by(email=request.values['email'],
                                email_token=request.values['token']).first()

    if user is None:
        raise RequestException('No email found matching that token.', 401)

    if user.verified:
        already_verified = True
    else:
        already_verified = False

    user.verified = True
    db.session.commit()

    context = {
        'already_verified': already_verified,
        'verified': True,
        'api_token': user.api_token,
        'jobs': [job for job in q.jobs if job.args[0] == user.email],
    }

    # Send an email with instructions and display on screen

    return render_template('verify.html', context=context)


@app.route('/', methods=['GET', 'POST'])
def home():
    """
    Present a simple form to register using email address
    and kindle email address.
    :return: Page to register or RequestException
    """
    form = RegisterForm()

    if form.validate_on_submit():
        '''
        Generate a new token for new users or create 
        a new token for existing users
        '''
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            user = User(email=form.email.data, kindle_email=form.kindle_email.data)
            db.session.add(user)
        else:
            user.verified = False
            user.kindle_email = form.kindle_email.data
            user.email_token = uuid4()
            user.api_token = uuid4()
        db.session.commit()

        # Send email to validate email
        send_email(to_email=user.email,
                   subject='Verify your email address',
                   plain_text='Click the link to verify your email address ' 
                              'and get instructions on how to start sending '
                              'web pages to your Kindle.'
                              '%sverify?token=%s&email=%s' % (request.url_root,
                                                              user.email_token,
                                                              user.email),
                   html='<p><a href="%sverify?token=%s&email=%s">Click here</a> '
                            'to verify your email address '
                            'and get instructions on how to start sending '
                            'web pages to your Kindle.</p>' % (request.url_root,
                                                               user.email_token,
                                                               user.email))

        return redirect(url_for('home') + '?email_sent=' + user.email)

    return render_template('home.html', form=form)
