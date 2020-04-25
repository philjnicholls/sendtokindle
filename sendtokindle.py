import requests
import smtplib
import ssl
import configparser

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase 
from email import encoders 
from bs4 import BeautifulSoup

URL = 'https://realpython.com/python-testing/'
#URL = 'https://www.ladybirdeducation.co.uk/the-importance-of-fairy-tales-in-the-efl-classroom/'

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


page = requests.get(URL, allow_redirects=True)

soup = BeautifulSoup(page.content, 'html.parser')
title = soup.find('title')

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
        'class': 'main-content',
    },
)

for path in paths_to_main:
    main = soup.find(path['element'],
        class_=path['class'] if 'class' in path else None
    )    
    if main:
        break

config = configparser.ConfigParser()
config.read('.sendtokindle.rc')

sender_email = config['SMTP']['EMAIL']
if 'USERNAME' in config['SMTP']:
    username = config['SMTP']['USERNAME']
else:
    username = sender_email
password = config['SMTP']['PASSWORD']
host = config['SMTP']['HOST']
port = config['SMTP']['PORT']
kindle_email = config['Kindle']['EMAIL']

# TODO Strip down the HTML to create a plain text version of the page
body_text = 'Just a test.'
body_html = str(main)

part1 = MIMEText(body_text, "plain")
part2 = MIMEText(body_html, "html")

message = MIMEMultipart("alternative")
message["Subject"] = title.text
message["From"] = sender_email
message["To"] = kindle_email

message.attach(part1)
message.attach(part2)

# open the file to be sent  
filename = title.text + '.html'

# instance of MIMEBase and named as p 
p = MIMEBase('application', 'octet-stream') 
  
# To change the payload into encoded form 
p.set_payload(body_html) 
  
# encode into base64 
encoders.encode_base64(p) 
   
p.add_header('Content-Disposition', "attachment; filename= %s" % filename) 
  
# attach the instance 'p' to instance 'msg' 
message.attach(p) 


context = ssl.create_default_context()
with smtplib.SMTP_SSL(host, port, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(
        sender_email, kindle_email, message.as_string()
    )
    server.quit()