FROM python:3-alpine

COPY articlescrape/requirements.txt requirements.txt
RUN apk add --no-cache libstdc++ libxml2-dev libxslt-dev \
	&& apk add --no-cache --virtual build-deps musl-dev g++ libffi-dev \
	&& python -m pip install --upgrade pip \
	&& python -m pip install -r requirements.txt \
	&& apk --purge del build-deps

RUN mkdir /service
COPY protobufs/ /service/protobufs/
COPY articlescrape/ /service/articlescrape/
COPY .env /service/articlescrape/.env
WORKDIR /service/articlescrape
WORKDIR /service
RUN python -m grpc_tools.protoc -I protobufs --python_out=articlescrape/ \
           --grpc_python_out=articlescrape/ protobufs/articlescrape.proto
WORKDIR /service/articlescrape

EXPOSE 50051
ENTRYPOINT [ "python", "articlescrape.py" ]
