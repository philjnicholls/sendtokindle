import base64
import grpc
import os
import re
import requests

from signal import signal, SIGTERM
from grpc_interceptor import ExceptionToStatusInterceptor
from concurrent import futures

from breadability.readable import Article as ReadableArticle
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

from articlescrape_pb2 import Article
import articlescrape_pb2_grpc

from dotenv import load_dotenv


class ArticleScrapeService(
    articlescrape_pb2_grpc.ArticleScrapeServicer
):
    def Scrape(self, request, context):
        driver = _new_driver()
        driver.get(request.url)

        doc = ReadableArticle(driver.page_source, url=request.url)

        def image_to_data_uri(image_src):
            if image_src[0:5] == 'data:':
                return image_src

            response = requests.get(image_src)
            if 'Content-Type' in response.headers:
                mime_type = response.headers['Content-Type']
            else:
                mime_type = 'image/png'
            image_bytes = BytesIO(response.content)
            base64_image = base64.b64encode(image_bytes.read()).decode()
            return f'data:{mime_type};base64,{base64_image}'

        # Convert all images to data uris so html is self-contained
        content = re.sub(
            r'(<img.+src=["\'])(.*?)(["\'])',
            lambda mo: '{}{}{}'.format(
                mo.group(1),
                image_to_data_uri(mo.group(2)),
                mo.group(3)),
            doc.readable
        )

        match = re.search(r'<title.*?>(.+?)</title>', driver.page_source,
                          re.IGNORECASE)
        if match:
            title = match.group(1)
        else:
            title = 'Web Article'


        return Article(
            title=title, content=content)


def _new_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--lang=en-us')
    capabilities = dict(DesiredCapabilities.CHROME)
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    selenium_host = os.getenv('SELENIUM_HOST')
    if selenium_host:
        driver = webdriver.Remote(
            selenium_host,
            desired_capabilities=capabilities,
            options=chrome_options)
    else:
        driver = webdriver.Chrome(
            desired_capabilities=capabilities,
            executable_path=os.environ.get("CHROMEDRIVER_PATH"),
            options=chrome_options)
    return driver


def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         interceptors=interceptors)
    articlescrape_pb2_grpc.add_ArticleScrapeServicer_to_server(
        ArticleScrapeService(), server
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
