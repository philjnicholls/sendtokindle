"""Tests for send to kindle.

__author__ = "Phil Nicholls"
__copyright__ = "Copyright 2020, Phil Nicholls"
__credits__ = ["Phil Nicholls"]
__license__ = "GNUv3"
__version__ = "0.1.0"
__maintainer__ = "Phil Nicholls"
__email__ = "phil.j.nicholls@gmail.com"
__status__ = "Development"
"""

import pytest

from redis import Redis
from rq import SimpleWorker, Queue

from app import app
from app.models import User

messages = []


@pytest.fixture(autouse=True)
def log_smtp(monkeypatch):
    """Prevent email being sent with SMTP and log instead."""
    global messages
    monkeypatch.setattr('smtplib.SMTP.login', lambda *args,
                        **kwargs: (235,
                                   ('Authentication '
                                    'successful')))
    monkeypatch.setattr('smtplib.SMTP.sendmail',
                        lambda *args: messages.append(args))


@pytest.fixture
def test_app(log_smtp):
    """Returns a test app."""
    app.config['WTF_CSRF_ENABLED'] = False
    return app.test_client()


@pytest.fixture
def api_token(log_smtp):
    """Return a validated api token."""
    app.config['WTF_CSRF_ENABLED'] = False
    test_app = app.test_client()
    payload = {
        'email': 'phil@example.com',
        'kindle_email': 'phil@example.com',
    }
    test_app.post('/', data=payload, follow_redirects=True)
    user = User.query.filter_by(email='phil@example.com').first()
    test_app.get(f'/verify?email={user.email}&token='
                 f'{user.email_token}')
    return user.api_token


def test_send_webpages(test_app, api_token, log_smtp):
    """Create RQ jobs for emailing webpages as articles."""
    global messages
    messages = []
    webpages = (
        'https://realpython.com/flask-blueprint/',
        'https://www.thedailybeast.com/mitzpe-ramon-israels-grand-canyon-'
        'is-from-another-world',
        'https://tinybuddha.com/blog/the-challenge-of-doing-less-when-'
        'youre-used-to-doing-more/',
        'https://www.freecodecamp.org/news/javascript-sleep-wait-delay/',
    )

    for webpage in webpages:
        payload = {
            'token': api_token,
            'url': webpage,
        }

        response = test_app.post('/api', data=payload)

        assert response.json is not None
        assert type(response.json['success']) == bool
        assert response.status_code == 200
        assert response.json['success']


def test_missing_url(test_app):
    """Error as URL is not supplied in payload."""
    payload = {}

    response = test_app.post('/api', data=payload)

    assert response.status_code == 400


def test_bad_url(test_app, api_token):
    """Error as supplied URL is not retrievable."""
    payload = {
        'token': api_token,
        'url': 'http://dgdgjs.fff/dhdgdyu'
    }

    response = test_app.post('/api', data=payload)

    assert response.status_code == 500


def test_queue(log_smtp, test_app, api_token):
    """Run the RQ queue to extract pages and send emails."""
    global messages
    messages = []
    payload = {
        'token': api_token,
        'url': 'https://realpython.com/flask-blueprint/',
    }

    test_app.post('/api', data=payload)
    queue = Queue(connection=Redis())

    assert len(queue.jobs) > 0

    worker = SimpleWorker([queue], connection=queue.connection)
    worker.work(burst=True)

    assert len(messages) > 0
