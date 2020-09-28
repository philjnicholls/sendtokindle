"""Class to support emailing of a webpage."""

import os
import re
import smtplib
import ssl
import tempfile
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from newspaper import Article, Config

import requests


class NoArticleHTMLException(Exception):
    """Failed to extract the article."""


class EmailWebpage:
    """Handles all the business around extracting HTML and emailing mobi."""

    def __init__(self,
                 email,
                 url,
                 html,
                 title,
                 smtp_user,
                 smtp_email,
                 smtp_password,
                 smtp_host,
                 smtp_port,
                 kindlegen_path,
                 append_html):
        """Initialize local vars, no actual processing takes place.

        :param email: email to send mobi turlo
        :param url: url to convert to mobi
        :param html: raw html to use for mobi
        :param title: title to use for the mobi
        :param smtp_user: SMTP server username
        :param smtp_email: SMTP server from address
        :param smtp_password: SMTP server password
        :param smtp_host: SMTP server host
        :param smtp_port: SMTP server port number
        :param kindlegen_path: Full path to the kindlegen binary
        :param append_html: raw HTML to append to the end of the mobi
        """
        self.email = email
        self.url = url
        self.html = html
        self.title = title
        self.append_html = append_html
        self.smtp = {
            'user': smtp_user,
            'email': smtp_email,
            'password': smtp_password,
            'host': smtp_host,
            'port': smtp_port,
        }
        self.kindlegen_path = kindlegen_path

    def send(self):
        """Get the webpage, convert to mobi and email.

        :raises NoArticleHTMLException: no article found
        """
        self.__get_page()
        if (self.article and self.article.article_html):
            with tempfile.TemporaryDirectory() as tmp_dir:
                self.__dump_images(tmp_dir)
                self.__send_kindle_email(tmp_dir)
        else:
            raise NoArticleHTMLException(f'Failed to get main article text '
                                         f'for {self.url}')

    def __get_page(self):
        """Download the page and parse."""
        # Setup some config for newspaper
        config = Config()
        config.keep_article_html = True
        config.follow_meta_refresh = True

        if self.url:
            self.article = Article(self.url, config=config)
            self.article.download()
            self.article.parse()
            self.article.fetch_images()
        else:
            # Hack passed HTML into Newspaper
            self.article = Article('file://')
            self.article.article_html = self.html
            self.article.title = self.title
            self.article.download(input_html=self.html)
            self.article.parse()
            self.article.fetch_images()

    def __dump_images(self, tmp_dir):
        """Write images to the supplied temporary directory.

        Ready for kindlgen to pick up

        :param tmp_dir: open temporary directory to store the images
        """
        for image in self.article.images:
            os.makedirs(os.path.join(tmp_dir,
                                     os.path.dirname(image)),
                        exist_ok=True)
            try:
                r = requests.get(image)
            except Exception:
                r = None

            if r:
                with open(os.path.join(tmp_dir, image), 'wb') as f:
                    f.write(r.content)
                    f.close()

    def __send_kindle_email(self, tmp_dir):
        """Send an ebook to a Kindle via email.

        :param tmp_dir: Currently open directory to use for
            mobi generation and source images
        """
        article_html = self.article.article_html
        article_title = self.article.title

        # Add HTML tags to make a valid HTML doc
        html_file = f"""<html>
                <head>
                    <title>{article_title}</title>
                    <meta http-equiv="Content-Type"
                        content="text/html; charset=UTF-8" />
                </head>
                <body><h1>{article_title}</h1>{article_html}{self.append_html}</body>
            </html>"""

        """
        Create a temporary file of the HTML and generate a mobi
        file from it
        """
        with tempfile.NamedTemporaryFile(dir=tmp_dir,
                                         suffix='.html',
                                         mode="w+") as temp_file:
            temp_file.write(html_file)
            temp_file.flush()
            os.system(self.kindlegen_path + ' ' + temp_file.name)
            mobi_path = os.path.splitext(temp_file.name)[0] + '.mobi'
            temp_file.close()

        self.__send_email(attachment_path=mobi_path,
                          attachment_title=os.path.basename(mobi_path))

    def __send_email(self, attachment_title, attachment_path):
        """Send an email with an attachment.

        Sends an email using SMTP settings from class with attached file

        :param attachment_title: Name of the file attachment
        :param attachment_path: Path to the attachment
        """
        message = MIMEMultipart("alternative")

        if self.article.text:
            part1 = MIMEText(self.article.text, "plain")
            message.attach(part1)
        if self.article.article_html:
            part2 = MIMEText(self.article.article_html, "html")
            message.attach(part2)

        message["Subject"] = self.article.title

        message["From"] = self.smtp['email']
        message["To"] = self.email

        if attachment_path and attachment_title:
            title_stripped = re.sub('[^A-Za-z0-9 ]+', '', attachment_title)

            # To change the payload into encoded form
            with open(attachment_path, "rb") as file:
                p = MIMEApplication(
                    file.read(),
                    Name=title_stripped
                )
                file.close()

            # encode into base64
            encoders.encode_base64(p)

            p.add_header(
                'Content-Disposition',
                'attachment; filename= %s' % title_stripped + '.mobi')

            # attach the instance 'p' to instance 'msg'
            message.attach(p)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.smtp['host'],
                              self.smtp['port'],
                              context=context) as server:
            server.login(self.smtp['user'], self.smtp['password'])
            server.sendmail(
                self.smtp['email'], self.email, message.as_string()
            )
