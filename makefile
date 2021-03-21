define USAGE

Commands:
	init			Install Python dependencies with pip
	serve			Run app in dev environment.
	run			Run app in docker
	build			Build docker container
endef

export USAGE
help:
	@echo "$$USAGE"

init:
	pip install -r requirements.txt

serve_articlescrape:
	GOOGLECHROMEBIN=/usr/bin/google-chrome CHROMEDRIVER_PATH=/usr/bin/googlechromedriver GRPC_PORT=50052 python articlescrape/articlescrape.py

run_articlescrape:
	docker run --env GOOGLECHROMEBIN=/usr/bin/google-chrome --env CHROMEDRIVER_PATH=/usr/bin/googlechromedriver --env GRPC_PORT=50052 -p 127.0.0.1:50052:50052/tcp articlescrape

build_articlescrape:
	docker build . -f articlescrape/Dockerfile -t articlescrape

serve_email:
	GRPC_PORT=50051 python email/send_mail.py

run_email:
	docker run --env GRPC_PORT=50051 -p 127.0.0.1:50051:50051/tcp email

build_email:
	docker build . -f email/Dockerfile -t email

serve_html2mobi:
	 GRPC_PORT=50053 KINDLEGEN=html2mobi/kindlegen python html2mobi/html2mobi.py

run_html2mobi:
	docker run --env GRPC_PORT=50053 --env KINDLEGEN=/service/html2mobi/kindlegen -p 127.0.0.1:50053:50053/tcp email

build_html2mobi:
	docker build . -f html2mobi/Dockerfile -t html2mobi

serve_website:
	HTML2MOBI_HOST=localhost:50053 EMAIL_HOST=localhost:50051 ARTICLESCRAPE_HOST=localhost:50052 FLASK_ENV=development DEBUG=True FLASK_APP=website/website.py flask run

run_website:
	docker run --env HTML2MOBI_HOST=localhost:50053 --env EMAIL_HOST=localhost:50051 --env ARTICLESCRAPE_HOST=localhost:50052 --env FLASK_APP=/service/website/website.py -p 127.0.0.1:5000:5000/tcp website

build_website:
	docker build . -f website/Dockerfile -t website

run_selenium:
	docker run -p 127.0.0.1:4444:4444/tcp selenium/standalone-chrome

serve_worker:
	HTML2MOBI_HOST=localhost:50053 EMAIL_HOST=localhost:50051 ARTICLESCRAPE_HOST=localhost:50052 REDIS_HOST=localhost:6379 python website/worker.py

run_worker:
	docker run --env HTML2MOBI_HOST=localhost:50053 --env EMAIL_HOST=localhost:50051 --env ARTICLESCRAPE_HOST=localhost:50052 --env REDIS_HOST=localhost:6379 worker

build_worker:
	docker build . -f worker/Dockerfile -t worker

run_webserver:
	docker run webserver

build_webserver:
	docker build . -f webserver/Dockerfile -t webserver

serve_all:
	make -j 5 serve_email serve_articlescrape serve_html2mobi serve_worker serve_website

build_all:
	make -j 6 build_email build_articlescrape build_html2mobi build_worker build_website build_webserver
