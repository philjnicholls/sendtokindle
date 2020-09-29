"""
Handle routes for web front-end and API.

__author__ = "Phil Nicholls"
__copyright__ = "Copyright 2020, Phil Nicholls"
__credits__ = ["Phil Nicholls"]
__license__ = "GNUv3"
__version__ = "0.1.0"
__maintainer__ = "Phil Nicholls"
__email__ = "phil.j.nicholls@gmail.com"
__status__ = "Development"
"""
import configparser
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlparse
from uuid import uuid4

from app import app
from app import db
from app import q
from app.EmailWebpage import EmailWebpage
from app.config import BASE_DIR
from app.extensions import csrf
from app.forms import RegisterForm
from app.forms import ReportArticleForm
from app.models import User

from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from github import Github

import requests
from requests.exceptions import RequestException

if not app.debug:
    @app.errorhandler(Exception)
    def handle_error(error):
        """Catch errors from the app.

        Try to send back a nice HTTP header and JSON response
        :param error: The error that has been raised
        :return: Json API response
        """
        message = [str(x) for x in error.args]

        status_code = None
        try:
            status_code = str(int(error.strerror))
        except AttributeError:
            status_code = '500'
        except TypeError:
            status_code = 500

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
    """Send an email.

    Use credentials from the .sendtokindle.rc file
    :param to_email: Recipient
    :param subject: Email subject
    :param html: HTML body for the email
    :param plain_text: Plain text body for the email
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
    """Get application configuration from rc file.

    :return: A config object
    :raises RequestException: Missing configuration file
    """
    if os.path.exists(os.path.join(BASE_DIR, '.sendtokindle.rc')):
        config = configparser.ConfigParser()
        config.read(os.path.join(BASE_DIR, '.sendtokindle.rc'))
        return config
    else:
        raise RequestException('Missing server config.', 404)


def process_and_send_page(email, url, html, title, report_url):
    """Extract main content from the URL and email.

    :param email: Recipient of the mobi file
    :param url: The URL to convert to a mobi
    :param html: HTML content for the mobi
    :param title: Title for mobi
    :param report_url: URL to bad article report form
    """
    config = get_config()

    report_html = (f'<mbp:pagebreak />'
                   f'Having trouble with this delivery? Is something not quite'
                   f'right?<a href="{report_url}">Send us a comment</a> and we'
                   f'\'ll do our best to keep improving the service. Thanks '
                   f'for the feedback and enjoy SendToKindle.')

    send_page = EmailWebpage(email=email,
                             url=url,
                             html=html,
                             title=title,
                             smtp_host=config['SMTP']['HOST'],
                             smtp_user=config['SMTP']['USERNAME'],
                             smtp_password=config['SMTP']['PASSWORD'],
                             smtp_port=config['SMTP']['PORT'],
                             smtp_email=config['SMTP']['EMAIL'],
                             kindlegen_path=os.path.join(BASE_DIR,
                                                         'kindlegen'),
                             append_html=report_html)
    send_page.send()


@app.route('/api', methods=['POST'])
@csrf.exempt
def send_page_to_kindle():
    """Public api to send webpage to kindle.

    :return: Json success response
    :raises RequestException: API errors
    """
    if 'url' not in request.json and 'html' not in request.json:
        raise RequestException('Missing parameter "url" or "html".', 400)

    if 'token' not in request.json:
        raise RequestException('Missing parameter "token".', 400)

    user = User.query.filter_by(api_token=request.json['token']).first()

    if not user:
        raise RequestException('No matching token found.', 401)

    if not user.verified:
        raise RequestException('You have not verified your email adress.', 401)

    if request.json.get('url', None):
        # Will raise exception is page doesn't exist or there's a problem
        requests.get(request.json['url'], allow_redirects=True)

    bad_article_url = url_for('report_bad_article')
    if 'url' in request.json:
        report_url = (f'{request.host_url}{bad_article_url}?'
                      f'url={request.json["url"]}&email={user.email}')
    else:
        report_url = (f'{request.host_url}{bad_article_url}?'
                      f'title={request.json["title"]}&email={user.email}')

    if app.debug:
        # If we're debugging then skip the queue to make life easier
        process_and_send_page(email=user.kindle_email,
                              url=request.json.get('url', None),
                              html=request.json.get('html', None),
                              title=request.json.get('title', None),
                              report_url=report_url)
    else:
        q.enqueue_call(
            func=process_and_send_page,
            args=(user.kindle_email,
                  request.json.get('url', None),
                  request.json.get('html', None),
                  request.json.get('title', None),
                  report_url),
            result_ttl=5000
        )

    return {'success': True}, 200


@app.route('/verify', methods=['GET'])
def verify():
    """Verify email ownership with email_token.

    :return: Response confirming verification
    :raises RequestException: API error
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
    """Present a simple form to register.

    Requires an email address and kindle email address.
    :return: Page to register or RequestException
    """
    form = RegisterForm()

    if form.validate_on_submit():
        """
        Generate a new token for new users or create
        a new token for existing users
        """
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            user = User(email=form.email.data,
                        kindle_email=form.kindle_email.data)
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
                   plain_text=(f'Click the link to verify your email address '
                               f'and get instructions on how to start sending '
                               f'web pages to your Kindle.'
                               f'{request.url_root}verify?token='
                               f'{user.email_token}&email={user.email}'),
                   html=(f'<p><a href="{request.url_root}verify?token='
                         f'{user.email_token}&email={user.email}">'
                         f'Click here</a> to verify your email address '
                         f'and get instructions on how to start sending '
                         f'web pages to your Kindle.</p>'))

        return redirect(url_for('home') + '?email_sent=' + user.email)

    return render_template('home.html', form=form)


@app.route('/report', methods=['GET', 'POST'])
def report_bad_article():
    """Web page to send reports of issues with articles.

    Present a simple form to allow posting of issues into
    GitHub repository.

    :return: Rendered template
    """
    form = ReportArticleForm(email=request.values.get('email', None),
                             url=request.values.get('url', None))

    if form.validate_on_submit():
        # Create a new issue on Github for later review

        uri = urlparse(form.url.data)
        title = f'Bad Article For {uri.netloc}'
        body = (f'URL: {form.url.data}\n'
                f'Email: {form.email.data}\n'
                f'Comment:{form.comment.data}')
        config = get_config()

        github = Github(config['GitHub']['ACCESS_TOKEN'])
        repo = github.get_repo(config['GitHub']['REPO_OWNER']
                               + '/' + config['GitHub']['REPO_NAME'])
        repo.create_issue(title=title,
                          body=body,
                          labels=['bad article'])

        return redirect(url_for('report_bad_article') + '?sent=1')

    return render_template('report_article.html', form=form)
