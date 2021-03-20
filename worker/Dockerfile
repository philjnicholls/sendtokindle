FROM python:3-alpine

COPY worker/requirements.txt requirements.txt
RUN apk add --no-cache libstdc++ \
	&& apk add --no-cache --virtual build-deps musl-dev g++ libffi-dev \
	&& python -m pip install --upgrade pip \
	&& python -m pip install -r requirements.txt \
	&& apk --purge del build-deps

RUN mkdir /service
COPY protobufs/ /service/protobufs/
COPY website/worker.py /service/worker/
COPY website/scrape_and_send.py /service/worker/
WORKDIR /service
RUN python -m grpc_tools.protoc -I protobufs --python_out=worker/ \
           --grpc_python_out=worker/ protobufs/articlescrape.proto
RUN python -m grpc_tools.protoc -I protobufs --python_out=worker/ \
           --grpc_python_out=worker/ protobufs/email.proto
RUN python -m grpc_tools.protoc -I protobufs --python_out=worker/ \
           --grpc_python_out=worker/ protobufs/html2mobi.proto
WORKDIR /service/worker

CMD ["python", "./worker.py"]
