import tempfile
import ssl
import smtplib
import re
import os
import requests

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from newspaper import Article, Config
from email import encoders


class NoArticleHTMLException(Exception):
    pass


class EmailWebpage:
    """
    Handles all the business around extracting HTML and emailing mobi
    """
    def __init__(self,
                 email,
                 url,
                 smtp_user,
                 smtp_email,
                 smtp_password,
                 smtp_host,
                 smtp_port,
                 kindlegen_path,
                 append_html):
        """
        Just setup local vars, no actual processing takes place
        :param email: email to send mobi to
        :param url: url to convert to mobi
        """
        self.email = email
        self.url = url
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
        """
        Gets the webpage, converts to mobi and emails to
        recipient
        :return:
        """
        self.__get_page()
        if self.article.article_html:
            with tempfile.TemporaryDirectory() as tmp_dir:
                self.__dump_images(tmp_dir)
                self.__send_kindle_email(tmp_dir)
        else:
            raise NoArticleHTMLException(f'Failed to get main article text for {self.url}')

    def __get_page(self):
        """
        Download the page and parse
        :param url: URL of the page to download
        :return:
        """
        # Setup some config for newspaper
        config = Config()
        config.keep_article_html = True
        config.follow_meta_refresh = True

        self.article = Article(self.url, config=config)
        self.article.download()
        self.article.parse()
        self.article.fetch_images()

    def __dump_images(self, tmp_dir):
        """
        Writes images to the supplied temporary directory so
        they are ready for kindlgen to pick up
        :param images: array of image URLs
        :param tmp_dir: open temporary directory to store
            the images
        :return:
        """
        for image in self.article.images:
            os.makedirs(os.path.join(tmp_dir, os.path.dirname(image)), exist_ok=True)
            try:
                r = requests.get(image)
            except Exception as e:
                r = None

            if r:
                with open(os.path.join(tmp_dir, image), 'wb') as f:
                    f.write(r.content)
                    f.close()

    def __send_kindle_email(self, tmp_dir):
        """
        Sends an email to the user matching the API token with an attached
        mobi file

        :param tmp_dir: Currently open directory to use for
            mobi generation and source images
        :return:
        """

        # Add HTML tags to make a valid HTML doc
        html_file = f'''<html>
                <head>
                    <title>{self.article.title}</title>
                    <meta http-equiv="Content-Type"
                        content="text/html; charset=UTF-8" />
                </head>
                <body><h1>{self.article.title}</h1>{self.article.article_html}{self.append_html}</body>
            </html>'''

        '''
        Create a temporary file of the HTML and generate a mobi
        file from it
        '''
        with tempfile.NamedTemporaryFile(dir=tmp_dir, suffix='.html', mode="w+") as temp_file:
            temp_file.write(html_file)
            temp_file.flush()
            os.system(self.kindlegen_path + ' ' + temp_file.name)
            mobi_path = os.path.splitext(temp_file.name)[0] + '.mobi'
            temp_file.close()

        self.__send_email(attachment_path=mobi_path,
                          attachment_title=os.path.basename(mobi_path))

    def __send_email(self, attachment_title, attachment_path):
        """
        Generic email sending with attachment

        :param attachment_title: Name of the file attachment
        :param attachment_path: Path to the attachment
        :return:
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
        with smtplib.SMTP_SSL(self.smtp['host'], self.smtp['port'], context=context) as server:
            server.login(self.smtp['user'], self.smtp['password'])
            server.sendmail(
                self.smtp['email'], self.email, message.as_string()
            )
            server.quit()
