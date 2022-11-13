# syntax=docker/dockerfile:1

FROM python:latest
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

EXPOSE 3000

CMD ["binance_data_collector", "start"]