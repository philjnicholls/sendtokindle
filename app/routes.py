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
from flask import request
from flask import jsonify
from flask import render_template
from flask import url_for
from flask import redirect
from uuid import uuid4
from newspaper import Article, Config
from rq.job import Job
from worker import conn

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

Runs as a Flask REST API on a webserver of your choice
'''


#@app.errorhandler(Exception)
def handle_error(error):
    '''
    Catches errors from the app and tries to send back
    a nice HTTP header and JSON response
    :param error: The error that has been raised
    :return:
    '''
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


class EmailWebpage():
    '''
    Handles all the business around extracting HTML and emailing mobi
    '''
    def __init__(self, email, url, smtp_user, smtp_email, smtp_password, smtp_host, smtp_port):
        '''
        Just setup local vars, no actual processing takes place
        :param email: email to send mobi to
        :param url: url to convert to mobi
        '''
        self.email = email
        self.url = url
        self.smtp = {
            'user': smtp_user,
            'email': smtp_email,
            'password': smtp_password,
            'host': smtp_host,
            'port': smtp_port,
        }

    def send(self):
        self.__get_page()
        if self.article.article_html:
            with tempfile.TemporaryDirectory() as tmp_dir:
                self.__dump_images(tmp_dir)
                self.__send_kindle_email(tmp_dir)

    def __get_page(self):
        '''
        Download the page and parse
        :param url: URL of the page to download
        :return:
        '''
        # Setup some config for newspaper
        config = Config()
        config.keep_article_html = True
        config.follow_meta_refresh = True

        self.article = Article(self.url, config=config)
        self.article.download()
        self.article.parse()
        self.article.fetch_images()

    def __dump_images(self, tmp_dir):
        '''
        Writes images to the supplied temporary directory so
        they are ready for kindlgen to pick up
        :param images: array of image URLs
        :param tmp_dir: open temporary directory to store
            the images
        :return:
        '''
        for image in self.article.images:
            os.makedirs(os.path.join(tmp_dir, os.path.dirname(image)), exist_ok=True)
            try:
                r = requests.get(image)
            except:
                r = None

            if r:
                with open(os.path.join(tmp_dir, image), 'wb') as f:
                    f.write(r.content)
                    f.close()

    def __send_kindle_email(self, tmp_dir):
        '''
        Sends an email to a user matching the API token with an attached
        mobi file

        :param tmp_dir: Currently open directory to use for
            mobi generation and source images
        :return:
        '''

        # Add HTML tags to make a valid HTML doc
        html_file = '''<html>
                <head>
                    <title>''' + self.article.title + '''</title>
                    <meta http-equiv="Content-Type"
                        content="text/html; charset=UTF-8" />
                </head>
                <body><h1>''' + self.article.title + '''</h1>''' + self.article.article_html + '''</body>
            </html>'''

        '''
        Create a temporary file of the HTML and generate a mobi
        file from it
        '''
        with tempfile.NamedTemporaryFile(dir=tmp_dir, suffix='.html', mode="w+") as temp_file:
            temp_file.write(html_file)
            temp_file.flush()
            os.system(os.path.join(BASE_DIR, 'kindlegen') + ' ' + temp_file.name)
            mobi_path = os.path.splitext(temp_file.name)[0] + '.mobi'
            temp_file.close()

        self.__send_email(attachment_path=mobi_path,
                   attachment_title=os.path.basename(mobi_path))

    def __send_email(self, attachment_title, attachment_path):

        message = MIMEMultipart("alternative")

        if self.article.text:
            part1 = MIMEText(self.article.text, "plain")
            message.attach(part1)
        if self.article.article_html:
            part2 = MIMEText(self.article.article_html, "html")
            message.attach(part2)

        message["Subject"] = self.article.title
        message["From"] = self.smtp['email']
        message["To"] = self.email

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
        with smtplib.SMTP_SSL(self.smtp['host'], self.smtp['port'], context=context) as server:
            server.login(self.smtp['user'], self.smtp['password'])
            server.sendmail(
                self.smtp['email'], self.email, message.as_string()
            )
            server.quit()

def send_email(to_email,
               subject,
               html=None,
               plain_text=None):
    '''
    Sends an email using redentials from the .sendtokindle.rc file
    :param to_email: Recipient
    :param subject: Email subject
    :param html: HTML body for the email
    :param plain_text: Plain text body for the email
    :param attachment_title: Name of the attachement as it will
        appear on the email
    :param attachment_path: Path to the attachement
    :return:
    '''

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
    message["From"] = sender_email
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
        raise requests.exceptions.RequestException('Missing server config.', 404)


def process_and_send_page(email, url):
    config = get_config()

    send_page = EmailWebpage(email=email,
                             url=url,
                             smtp_host=config['SMTP']['HOST'],
                             smtp_user=config['SMTP']['USERNAME'],
                             smtp_password=config['SMTP']['PASSWORD'],
                             smtp_port=config['SMTP']['PORT'],
                             smtp_email=config['SMTP']['EMAIL'])
    send_page.send()

@app.route('/api', methods=['POST'])
@csrf.exempt
def send_page_to_kindle():
    '''
    Public api which takes a token and url, finds the main page content
    and emails it as a mobi file.
    :return:
    '''

    # If no URL is specified, raise an error
    if 'url' not in request.values:
        raise requests.exceptions.RequestException('Missing parameter "url".', 400)

    if 'token' not in request.values:
        raise requests.exceptions.RequestException('Missing parameter "token".', 400)

    user = User.query.filter_by(api_token=request.values['token']).first()

    if not user:
        raise requests.exceptions.RequestException('No matching token found.', 401)

    if not user.verified:
        raise requests.exceptions.RequestException('You have not verified your email adress.', 401)

    job = q.enqueue_call(
        func = process_and_send_page, args = (user.kindle_email, request.values['url']), result_ttl = 5000
    )
    print(job.get_id())

    return {'success': True}, 200


@app.route('/verify', methods=['GET'])
def verify():
    '''
    Verify email ownership with email_token
    :return: Response confirming verification or RequestException
    '''
    user = User.query.filter_by(email=request.values['email'],
                                email_token=request.values['token']).first()

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
    :return: Page to register or RequestException
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
            user.kindle_email = form.kindle_email.data
            user.email_token = uuid4()
            user.api_token = uuid4()
        db.session.commit()

        # Send email to validate email
        send_email(to_email=user.email,
                   subject='Verify your email address',
                   plain_text='%sverify?token=%s&email=%s' % (request.url_root,
                                                              user.email_token,
                                                              user.email))

        return redirect(url_for('home') + '?email_sent=' + user.email)

    return render_template('home.html', form=form)
