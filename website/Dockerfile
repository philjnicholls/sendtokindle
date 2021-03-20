FROM python:3.8-alpine

COPY website/requirements.txt requirements.txt
RUN apk add --no-cache postgresql-libs uwsgi-python3 libstdc++ \
	&& apk add --no-cache --virtual build-deps musl-dev g++ libffi-dev postgresql-dev \
	&& python -m pip install --upgrade pip \
	&& python -m pip install -r requirements.txt \
	&& apk --purge del build-deps

RUN mkdir /service
COPY protobufs/ /service/protobufs/
COPY website/ /service/website/
COPY .env /service/website/app/.env

WORKDIR /service
RUN python -m grpc_tools.protoc -I protobufs --python_out=website/ \
           --grpc_python_out=website/ protobufs/articlescrape.proto
RUN python -m grpc_tools.protoc -I protobufs --python_out=website/ \
           --grpc_python_out=website/ protobufs/email.proto
RUN python -m grpc_tools.protoc -I protobufs --python_out=website/ \
           --grpc_python_out=website/ protobufs/html2mobi.proto
WORKDIR /service/website

CMD [ "uwsgi", "--socket", "0.0.0.0:3031", \
	       "--master", \
	       "--processes", "5", \
               "--uid", "uwsgi", \
               "--plugins", "python3", \
               "--protocol", "uwsgi", \
	       "-H", "/usr/local", \
               "--wsgi", "app:app" ]

EXPOSE 3031
