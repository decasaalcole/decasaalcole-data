FROM ubuntu:20.04
WORKDIR /usr/local/app/

ENV LANG C.UTF-8
ENV BUILD_DIR /usr/src/
ENV POETRY_VERSION=1.1.4

COPY ./ ${BUILD_DIR}

RUN set -ex ; \
    if [ $ENVIRONMENT = "local" ] || [ $ENVIRONMENT = "test" ]  ; then \
      POETRY_EXTRA="" ; \
    else \
      POETRY_EXTRA="--no-dev" ; \
    fi ; \
    apt-get update ; \
    apt-get install -y python3-pip; \
    pip3 install --upgrade setuptools ; \
    pip3 install "poetry==$POETRY_VERSION" ; \
    cd ${BUILD_DIR}; \
    poetry config virtualenvs.create false ; \
    poetry install --no-interaction --no-ansi $POETRY_EXTRA ; \
    apt-get remove -y --purge python3-pip; \
    rm -rf ${BUILD_DIR}/*;

COPY ./ /usr/local/app/
