"""Configuration for the application."""
import os
import requests
import configparser


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    """Get app config from rc file."""

    # Get the SQL connection settings from settings rc file
    if os.path.exists(os.path.join(BASE_DIR, '.sendtokindle.rc')):
        config = configparser.ConfigParser()
        config.read(os.path.join(BASE_DIR, '.sendtokindle.rc'))
    else:
        raise requests.exceptions.RequestException('Missing database config.',
                                                   404)

    SQLALCHEMY_DATABASE_URI = (f'sqlite:///sendtokindle.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
