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
import os
import grpc

from uuid import uuid4

from app import app
from app import db
from app import q
from app.extensions import csrf
from app.forms import RegisterForm
from app.models import User

from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from email_pb2_grpc import EmailStub
from email_pb2 import EmailMessage, EmailAddress

import requests
from requests.exceptions import RequestException

from scrape_and_send import scrape_and_send


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
            status_code = '500 '
        except TypeError:
            status_code = '500 '

        if not status_code:
            status_code = '500 '

        success = False
        response = {
            'success': success,
            'error': {
                'type': error.__class__.__name__,
                'message': message,
            }
        }

        return jsonify(response), status_code


@app.route('/api', methods=['POST', 'GET'])
@csrf.exempt
def send_page_to_kindle():
    """Public api to send webpage to kindle.

    :return: Json success response
    :raises RequestException: API errors
    """
    context = {}
    required_params = ('url', 'token')
    if request.json and all([param in request.json for param in
                             required_params]):
        url = request.json['url']
        token = request.json['token']
    elif request.args and all([param in request.args for param in
                              required_params]):
        url = request.args['url']
        token = request.args['token']
    else:
        raise RequestException('Missing parameters', 400)

    context['url'] = url

    user = User.query.filter_by(api_token=token).first()

    if not user:
        raise RequestException('No matching token found.', 401)

    if not user.verified:
        raise RequestException('You have not verified your email adress.', 401)

    context['kindle_email'] = user.kindle_email

    if url:
        # Will raise exception is page doesn't exist or there's a problem
        requests.get(url, allow_redirects=True)

    q.enqueue_call(
        func=scrape_and_send, args=(url, user.kindle_email), result_ttl=5000
    )

    if request.json:
        return {'success': True}, 200
    else:
        return render_template('sent.html', context=context)


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
            user.email_token = str(uuid4())
            user.api_token = str(uuid4())
        db.session.commit()

        # Send email to validate email
        email_channel = grpc.insecure_channel(os.getenv('EMAIL_HOST'))
        email_client = EmailStub(email_channel)
        message = EmailMessage(
            to=[EmailAddress(email=user.email)],
            sender=EmailAddress(email='phil.j.nicholls@gmail.com'),
            subject='Verify your email address',
            body_text=(f'Click the link to verify your email address '
                       f'and get instructions on how to start sending '
                       f'web pages to your Kindle.'
                       f'{request.url_root}verify?token='
                       f'{user.email_token}&email={user.email}'),
            body_html=(f'<p><a href="{request.url_root}verify?token='
                       f'{user.email_token}&email={user.email}">'
                       f'Click here</a> to verify your email address '
                       f'and get instructions on how to start sending '
                       f'web pages to your Kindle.</p>')
        )
        response = email_client.Send(
            message
        )
        breakpoint()

        return redirect(url_for('home') + '?email_sent=' + user.email)

    return render_template('home.html', form=form)
