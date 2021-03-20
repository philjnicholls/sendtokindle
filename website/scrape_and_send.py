import grpc
import os

from articlescrape_pb2 import ScrapeRequest
from articlescrape_pb2_grpc import ArticleScrapeStub
from email_pb2 import EmailMessage, EmailAddress, Attachment
from email_pb2_grpc import EmailStub
from html2mobi_pb2 import MOBI
from html2mobi_pb2_grpc import HTML2MOBIStub

def scrape_and_send(url, kindle_email):
    articlescrape_channel = grpc.insecure_channel(os.getenv('ARTICLESCRAPE_HOST'))
    articlescrape_client = ArticleScrapeStub(articlescrape_channel)

    html2mobi_channel = grpc.insecure_channel(os.getenv('HTML2MOBI_HOST'))
    html2mobi_client = HTML2MOBIStub(html2mobi_channel)

    email_channel = grpc.insecure_channel(os.getenv('EMAIL_HOST'))
    email_client = EmailStub(email_channel)

    articlescrape_request = ScrapeRequest(
        url=url
    )
    article = articlescrape_client.Scrape(
        articlescrape_request
    )
    mobi = html2mobi_client.Convert(
        article
    )
    message = EmailMessage(
        to=[EmailAddress(email=kindle_email)],
        sender=EmailAddress(email='phil.j.nicholls@gmail.com'),
        subject=article.title,
        body_text='',
        body_html='',
        attachments=[Attachment(name=f'{article.title}.mobi', file=mobi.file)]
    )
    response = email_client.Send(
        message
    )
