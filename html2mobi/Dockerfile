FROM python:3-alpine

COPY html2mobi/requirements.txt requirements.txt
RUN apk add --no-cache libstdc++ \
	&& apk add --no-cache --virtual build-deps musl-dev g++ libffi-dev \
	&& python -m pip install --upgrade pip \
	&& python -m pip install -r requirements.txt \
	&& apk --purge del build-deps

RUN mkdir /service
COPY protobufs/ /service/protobufs/
COPY html2mobi/ /service/html2mobi/
COPY .env /service/html2mobi/.env
WORKDIR /service
RUN python -m grpc_tools.protoc -I protobufs --python_out=html2mobi/ \
        --grpc_python_out=html2mobi/ protobufs/html2mobi.proto
RUN python -m grpc_tools.protoc -I protobufs --python_out=html2mobi/ \
        --grpc_python_out=html2mobi/ protobufs/articlescrape.proto
WORKDIR /service/html2mobi

EXPOSE 50051
ENTRYPOINT [ "python", "html2mobi.py" ]
