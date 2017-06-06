FROM alpine:3.6

# Install dependencies
RUN apk add --no-cache python3
RUN apk add --no-cache --virtual build-dependencies \
                      curl                          \
                      fontconfig                    \
                      gcc                           \
                      libffi-dev                    \
                      musl-dev                      \
                      openssl-dev                   \
                      python3-dev

# Install phantomjs
RUN mkdir -p /usr/share
WORKDIR /usr/share
RUN curl -L https://github.com/Overbryd/docker-phantomjs-alpine/releases/download/2.11/phantomjs-alpine-x86_64.tar.bz2 | tar xj \
 && ln -s /usr/share/phantomjs/phantomjs /usr/bin/phantomjs \
 && phantomjs --version

# Copy Privacy Bot inside of Docker
COPY privacy_bot/ /tmp/privacy_bot
COPY setup.py /tmp/

# Install Privacy Bot
WORKDIR /tmp
RUN python3 -m ensurepip                            \
 && pip3 install --upgrade pip setuptools           \
 && pip3 install cython                             \
 && pip3 install requests[security]                 \
 && pip3 install -e .

# Clean-up
RUN apk del build-dependencies                      \
 && rm -rv /usr/lib/python*/ensurepip               \
 && rm -rv /root/.cache
