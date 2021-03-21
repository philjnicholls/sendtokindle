from signal import signal, SIGTERM
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import InvalidArgument

from concurrent import futures

import grpc
import os
import tempfile
import re


from html2mobi_pb2 import MOBI
from articlescrape_pb2 import Article

from dotenv import load_dotenv

import html2mobi_pb2_grpc


class HTML2MOBIService(
    html2mobi_pb2_grpc.HTML2MOBIServicer
):
    def Convert(self, request, context):
        kindlegen_path = os.getenv('KINDLEGEN')

        if not all([kindlegen_path]):
            raise InvalidArgument("You must set KINDLEGEN.")

        content = (
            f'''
<html>
    <head>
        <title>{request.title}</title>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    </head>
    <body>
        {request.content}
    </body>
</html>'''
        )

        with tempfile.NamedTemporaryFile(suffix='.html',
                                         mode="w+") as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.system(f'{kindlegen_path} {temp_file.name}')
            # TODO Check result of system call
            mobi_path = os.path.splitext(temp_file.name)[0] + '.mobi'
            temp_file.close()

        with open(mobi_path, 'rb') as f:
            mobi = f.read()

        os.remove(mobi_path)
        return MOBI(file=mobi)


def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         interceptors=interceptors)
    html2mobi_pb2_grpc.add_HTML2MOBIServicer_to_server(
        HTML2MOBIService(), server
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
