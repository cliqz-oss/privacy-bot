FROM alpine:3.5

ADD privacy_bot /tmp/privacy_bot
ADD setup.py /tmp/
RUN apk add --no-cache python3 gcc musl-dev libxml2-dev libxslt-dev python3-dev libffi-dev openssl-dev && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    pip3 install six && \
    pip3 install requests[security] && \
    rm -r /root/.cache && \
    cd /tmp/ && \
    pip3 install -e .
