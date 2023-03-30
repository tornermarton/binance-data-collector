# syntax=docker/dockerfile:1

FROM python:3.10
MAINTAINER tornermarton

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV NOTVISIBLE "in users profile"

WORKDIR /

############## INSTALL APPLICATION ################

# Install app
RUN mkdir /app /data
COPY . /app
RUN cd /app && make install

ENV DATA_ROOT /data

EXPOSE 3000

CMD ["binance_data_collector", "start"]