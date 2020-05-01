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

app = flask.Flask(__name__)

ATTRIBUTE_BLACKLIST = ['style']
TAG_BLACKLIST = ['script', 'style']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

URL = 'https://realpython.com/python-testing/'
'''
URL = ('https://www.ladybirdeducation.co.uk/'
            'the-importance-of-fairy-tales-in-the-efl-classroom/')
'''

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
a Kindle for easy reading on the eyes
'''


@app.route('/', methods=['POST'])
def send_page_to_kindle():
    if 'url' in request.values:
        url = request.values['url']
    else:
        url = URL
    page = requests.get(url, allow_redirects=True)

    soup = BeautifulSoup(page.content, 'html.parser')

    # Strip the styling and unwanted from the page
    for tag in soup.findAll():
        if tag.name.lower() in TAG_BLACKLIST:
            del tag
        # TODO Strip attributes

    title = soup.title.string

    '''
    Try to get a main HTML element which should have the
    main body of the webpage
    '''

    paths_to_main = (
        {
            'element': 'main',
        },
        {
            'element': 'article',
        },
        {
            'element': 'div',
            'class': 'article-content-container',
        },
        {
            'element': 'div',
            'class': 'main-content',
        },
        {
            'element': 'div',
            'id': 'main',
        },
        {
            'element': 'div',
            'id': 'content',
        },
    )

    # Search the HTML for the main content
    for path in paths_to_main:
        main = soup.find(
            path['element'],
            class_=path['class'] if 'class' in path else None,
            id=path['id'] if 'id' in path else None
        )
        if main:
            break

    config = configparser.ConfigParser()
    config.read(os.path.join(BASE_DIR, '.sendtokindle.rc'))

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
    TODO Strip down the HTML to create a plain
    text version of the page
    '''
    body_text = main.get_text()
    html_file = '''<html>
        <head>
            <title>''' + title + '''</title>
            <meta http-equiv="Content-Type"
                content="text/html; charset=UTF-8" />
        </head>
        <body>''' + str(main) + '''</body>
    </html>'''

    temp_file = tempfile.NamedTemporaryFile(suffix='.html')
    temp_file.write(bytes(html_file, 'UTF-8'))
    os.system(os.path.join(BASE_DIR, 'kindlegen') + ' ' + temp_file.name)
    mobi_path = os.path.splitext(temp_file.name)[0] + '.mobi'
    temp_file.close()

    body_html = html_file

    part1 = MIMEText(body_text, "plain")
    part2 = MIMEText(body_html, "html")

    message = MIMEMultipart("alternative")
    message["Subject"] = title
    message["From"] = sender_email
    message["To"] = kindle_email

    message.attach(part1)
    message.attach(part2)

    # open the file to be sent
    filename = title + '.html'

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
        server.login(sender_email, password)
        server.sendmail(
            sender_email, kindle_email, message.as_string()
        )
        server.quit()

    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=True)