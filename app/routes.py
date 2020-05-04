import requests
import smtplib
import ssl
import configparser
import re
import os
import tempfile

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email import encoders
from bs4 import BeautifulSoup
from flask import request
from flask import jsonify
from flask import render_template
from flask import url_for
from flask import redirect
from uuid import uuid4

from app import app
from app import db
from app.models import User
from app.forms import RegisterForm
from app.extensions import csrf

'''
Attributes and tags that will be removed from 
the scraped HTML
'''
ATTRIBUTE_BLACKLIST = ['style']
TAG_BLACKLIST = ['script', 'style']

# Project directory for file access
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

Runs as a Flask REST API on a webserver of your choice
'''

#@app.errorhandler(Exception)
def handle_error(error):
    message = [str(x) for x in error.args]

    status_code = None
    try:
        status_code = str(int(error.strerror))
    except ValueError or TypeError:
        status_code = '500'

    if not status_code:
        status_code = '500'

    success = False
    response = {
        'success': success,
        'error': {
            'type': error.__class__.__name__,
            'message': message
        }
    }

    return jsonify(response), status_code

def check_arguments(values):
    '''
    Checks request object for required arguments and
    passes back a cleaned dict of them.

    :param request: The HTTP request object
    :return: A clean dict of arguments
    '''
    cleaned = {}

    # If no URL is specified, raise an error
    if 'url' in values:
        cleaned['url'] = request.values['url']

    if 'token' in values:
        cleaned['token'] = request.values['token']

    return cleaned


def get_main_content(soup):
    '''
    Try to get a main HTML element which should have the
    main body of the webpage
    '''

    paths_to_main = (
        {
            'element': 'main',
            'kwargs': {},
        },
        {
            'element': 'article',
            'kwargs': {},
        },
        {
            'element': 'div',
            'kwargs': {
                'class_': 'article-content-container',
            }
        },
        {
            'element': 'div',
            'kwargs': {
                'class_': 'main-content',
            }
        },
        {
            'element': 'div',
            'kwargs': {
                'id': 'main',
            }
        },
        {
            'element': 'div',
            'kwargs': {
                'id': 'content',
            }
        },
    )

    # Search the HTML for the main content
    for path in paths_to_main:
        main = soup.find(
            path['element'],
            **path['kwargs']
        )
        if main:
            break

    return main

def send_email(config, to_email, subject, html=None, plain_text=None, attachment_title=None, attachment_path=None):

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
    message["From"] = sender_email
    message["To"] = to_email

    if attachment_path and attachment_title:
        title_stripped = re.sub('[^A-Za-z0-9 ]+', '', attachment_title)

        # To change the payload into encoded form
        with open(attachment_path, "rb") as file:
            p = MIMEApplication(
                file.read(),
                Name=title_stripped
            )
            file.close()

        # encode into base64
        encoders.encode_base64(p)

        p.add_header(
            'Content-Disposition',
            'attachment; filename= %s' % title_stripped + '.mobi')

        # attach the instance 'p' to instance 'msg'
        message.attach(p)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(username, password)
        server.sendmail(
            sender_email, to_email, message.as_string()
        )
        server.quit()

def send_kindle_email(token, config, title, html):
    user = User.query.filter_by(api_token=token).first()
    if not user:
        raise requests.exceptions.RequestException('No matching token found.', 401)

    if not user.verified:
        raise requests.exceptions.RequestException('You have not verified your email adress.', 401)

    '''
        Add HTML tags to make a valid HTML doc
        '''
    html_file = '''<html>
            <head>
                <title>''' + title + '''</title>
                <meta http-equiv="Content-Type"
                    content="text/html; charset=UTF-8" />
            </head>
            <body>''' + html + '''</body>
        </html>'''

    '''
    Create a temporary file of the HTML and generate a mobi
    file from it
    '''
    temp_file = tempfile.NamedTemporaryFile(suffix='.html')
    temp_file.write(bytes(html_file, 'UTF-8'))
    os.system(os.path.join(BASE_DIR, 'kindlegen') + ' ' + temp_file.name)
    mobi_path = os.path.splitext(temp_file.name)[0] + '.mobi'
    temp_file.close()

    send_email(config=config, to_email=user.email, subject=title, attachment_path=mobi_path, attachment_title=os.path.basename(mobi_path))

def get_config():
    if os.path.exists(os.path.join(BASE_DIR, '.sendtokindle.rc')):
        config = configparser.ConfigParser()
        config.read(os.path.join(BASE_DIR, '.sendtokindle.rc'))
        return config
    else:
        raise requests.exceptions.RequestException('Missing server config.', 404)

@app.route('/api', methods=['POST'])
@csrf.exempt
def send_page_to_kindle():
    # Check for the required parameters
    args = check_arguments(request.values)
    if 'url' not in args:
        raise requests.exceptions.RequestException('Missing parameter "url".', 400)

    # Get the page
    page = requests.get(args['url'], allow_redirects=True)

    if page.status_code == 404:
        raise requests.exceptions.RequestException('Unable to find "%s"' % args['url'], 404)

    soup = BeautifulSoup(page.content, 'html.parser')

    # Strip the styling and unwanted from the page
    for tag in soup.findAll():
        for attr in [attr for attr in tag.attrs if attr in ATTRIBUTE_BLACKLIST]:
            del tag[attr]
        if tag.name.lower() in TAG_BLACKLIST:
            del tag

    title = soup.title.string

    main = get_main_content(soup)

    if main:
        config = get_config()

        send_kindle_email(token=args['token'], config=config, title=title, html=str(main))

        return {'success': True}, 200

    else:
        raise requests.exceptions.RequestException('Failed to find the main content for the webpage.', 500)


@app.route('/verify', methods=['GET'])
def verify():
    '''
    Verify email ownership by following link in
    email
    :return:
    '''
    user = User.query.filter_by(email=request.values['email'], email_token=request.values['token']).first()

    if user is None:
        raise requests.exceptions.RequestException('No email found matching that token.', 401)

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
    }

    # Send an email with instructions and display on screen

    return render_template('verify.html', context=context)

@app.route('/', methods=['GET', 'POST'])
def home():
    '''
    Present a simple form to register using email address
    and kindle email address.
    :return:
    '''
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
            user.api_token = uuid4()
        db.session.commit()

        # Send email to validate email
        config = get_config()
        send_email(config=config,
                   to_email=user.email,
                   subject='Verify your email address',
                   plain_text='%sverify?token=%s&email=%s' % (request.url_root, user.email_token, user.email))

        return redirect(url_for('home') + '?token=' + user.api_token)

    return render_template('home.html', form=form)
