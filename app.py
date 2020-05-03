import requests
import smtplib
import ssl
import configparser
import re
import flask
import json
import os
import sys
import tempfile

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from bs4 import BeautifulSoup
from flask import request
from flask import jsonify
from flask_cors import CORS

app = flask.Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

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


def send_email(config, title, html, plain_text):

    sender_email = config['SMTP']['EMAIL']
    if 'USERNAME' in config['SMTP']:
        username = config['SMTP']['USERNAME']
    else:
        username = sender_email
    password = config['SMTP']['PASSWORD']
    host = config['SMTP']['HOST']
    port = config['SMTP']['PORT']
    kindle_email = config['Kindle']['EMAIL']

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

    part1 = MIMEText(plain_text, "plain")
    part2 = MIMEText(html_file, "html")

    message = MIMEMultipart("alternative")
    message["Subject"] = title
    message["From"] = sender_email
    message["To"] = kindle_email

    message.attach(part1)
    message.attach(part2)

    title_stripped = re.sub('[^A-Za-z0-9 ]+', '', title)

    # To change the payload into encoded form
    with open(mobi_path, "rb") as mobi_file:
        p = MIMEApplication(
            mobi_file.read(),
            Name=title_stripped + '.mobi'
        )
        mobi_file.close()

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
            sender_email, kindle_email, message.as_string()
        )
        server.quit()


@app.route('/', methods=['POST'])
def send_page_to_kindle():
    # Check for the required parameters
    args = check_arguments(request.values)
    if 'url' not in args:
        return 'Missing parameter "url".', 400

    # Get the page
    try:
        page = requests.get(args['url'], allow_redirects=True)
    except requests.exceptions.RequestException as e:
        return str(e), 404

    soup = BeautifulSoup(page.content, 'html.parser')

    # Strip the styling and unwanted from the page
    for tag in soup.findAll():
        for attr in [attr for attr in tag.attrs if attr in ATTRIBUTE_BLACKLIST]:
            del tag[attr]
        if tag.name.lower() in TAG_BLACKLIST:
            del tag

    title = soup.title.string

    main = get_main_content(soup)

    if os.path.exists(os.path.join(BASE_DIR, '.sendtokindle.rc')):
        config = configparser.ConfigParser()
        config.read(os.path.join(BASE_DIR, '.sendtokindle.rc'))
    else:
        return 'Missing server config.', 404

    '''
    TODO Strip down the HTML to create a plain
    text version of the page
    '''
    plain_text = main.get_text()

    send_email(config, title, str(main), plain_text)

    return {'success': True}


if __name__ == '__main__':
    app.run(debug=True)
