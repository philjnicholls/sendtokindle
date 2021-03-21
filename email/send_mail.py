import email_pb2_grpc
import grpc
import os
import re
import smtplib
import ssl

from signal import signal, SIGTERM
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import InvalidArgument

from concurrent import futures

from email_pb2 import EmailMessage, EmailResponse

from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv


class EmailService(
    email_pb2_grpc.EmailServicer
):
    def Send(self, request, context):
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = os.getenv('SMTP_PORT')
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')

        if not all([smtp_host, smtp_port, smtp_username, smtp_password]):
            raise InvalidArgument(
                "You must set SMTP_HOST, SMTP_PORT, "
                "SMTP_USERNAME and SMTP_PASSWORD.")

        sender = request.sender
        to = request.to
        subject = request.subject
        body_text = request.body_text
        body_html = request.body_html

        message = MIMEMultipart("alternative")

        if body_text:
            body_text_part = MIMEText(body_text, "plain")
            message.attach(body_text_part)
        if body_html:
            body_html_part = MIMEText(body_html, "html")
            message.attach(body_html_part)

        message["Subject"] = subject

        message["From"] = f'{sender.name} <{sender.email}>'

        message["To"] = ','.join([f'{recipient.name} <{recipient.email}>'
                                  for recipient in to])

        for attachment in request.attachments:
            filename, ext = os.path.splitext(attachment.name)
            filename = re.sub('[^A-Za-z0-9 ]+', '', filename)
            name_stripped = f'{filename}{ext}'

            p = MIMEApplication(
                attachment.file,
                Name=attachment.name
            )

            encoders.encode_base64(p)

            p.add_header(
                'Content-Disposition',
                f'attachment; filename={name_stripped}')

            message.attach(p)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host,
                              smtp_port,
                              context=context) as server:
            server.login(smtp_username, smtp_password)
            server.sendmail(
                sender.email,
                ','.join([recipient.email for recipient in to]),
                message.as_string()
            )

        return EmailResponse(
            response=f'Email sent to {message["To"]}')

def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         interceptors=interceptors)
    email_pb2_grpc.add_EmailServicer_to_server(
        EmailService(), server
    )
    port = os.getenv('GRPC_PORT', 50051)
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    def handle_sigterm(*_):
        print("Received shutdown signal")
        all_rpcs_done_event = server.stop(30)
        all_rpcs_done_event.wait(30)
        print("Shut down gracefully")

    signal(SIGTERM, handle_sigterm)
    server.wait_for_termination()


if __name__ == "__main__":
    load_dotenv()
    serve()
