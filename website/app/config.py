import os

"""Configuration for the application."""
class Config(object):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///sendtokindle.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
