import os
import requests
import configparser

from os import environ


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    if os.path.exists(os.path.join(BASE_DIR, 'mysql.cnf')):
        config = configparser.ConfigParser()
        config.read(os.path.join(BASE_DIR, 'mysql.cnf'))
    else:
        raise requests.exceptions.RequestException('Missing database config.', 404)

    SQLALCHEMY_DATABASE_URI = 'mysql://%s:%s@%s/%s' % (config['client']['user'],
                                                       config['client']['password'],
                                                       config['client']['host'],
                                                       config['client']['database'])
    SQLALCHEMY_TRACK_MODIFICATIONS = False