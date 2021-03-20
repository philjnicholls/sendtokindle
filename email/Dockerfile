FROM python:3-alpine

COPY email/requirements.txt requirements.txt
RUN apk add --no-cache libstdc++ \
	&& apk add --no-cache --virtual build-deps musl-dev g++ libffi-dev \
	&& python -m pip install --upgrade pip \
	&& python -m pip install -r requirements.txt \
	&& apk --purge del build-deps

RUN mkdir /service
COPY protobufs/ /service/protobufs/
COPY email/ /service/email/
COPY .env /service/email/.env
WORKDIR /service
RUN python -m grpc_tools.protoc -I protobufs --python_out=email/ \
        --grpc_python_out=email/ protobufs/email.proto
WORKDIR /service/email

EXPOSE 50051
ENTRYPOINT [ "python", "send_mail.py" ]
