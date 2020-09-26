import pytest

from app import app
from app.models import User

'''
__author__ = "Phil Nicholls"
__copyright__ = "Copyright 2020, Phil Nicholls"
__credits__ = ["Phil Nicholls"]
__license__ = "GNUv3"
__version__ = "0.1.0"
__maintainer__ = "Phil Nicholls"
__email__ = "phil.j.nicholls@gmail.com"
__status__ = "Development"
'''


@pytest.fixture
def test_app():
    app.config['WTF_CSRF_ENABLED'] = False
    return app.test_client()


@pytest.fixture
def api_token():
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


def test_send_webpages(test_app, api_token):
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
    payload = {}

    response = test_app.post('/api', data=payload)

    assert response.status_code == 400


def test_bad_url(test_app, api_token):
    payload = {
        'token': api_token,
        'url': 'http://dgdgjs.fff/dhdgdyu'
    }

    response = test_app.post('/api', data=payload)

    assert response.status_code == 500
