define USAGE

Commands:
	init		Install Python dependencies with pip
	test      	Run tests
	serve_website	Run app in dev environment.
	serve_queue	Run queue in dev environment.
endef

export USAGE
help:
	@echo "$$USAGE"

init:
	pip install -r requirements/common.txt

test:
	pytest --flake8 --cov --cov-report term-missing

serve_website:
	flask run

serve_queue:
	python worker.py
