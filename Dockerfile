# syntax=docker/dockerfile:1

FROM python:latest
MAINTAINER tornermarton

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV NOTVISIBLE "in users profile"

WORKDIR /

############## INSTALL REQUIREMENTS ################

# Install system packages
RUN apt -q update --fix-missing

# Install ssh server
RUN apt -q install -y openssh-server

# Install supervisord
RUN apt -q install -y supervisor

# Cleanup
RUN apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

############## CONFIGURE ################

# Remove login messages
RUN chmod -x /etc/update-motd.d/*

# Configure ssh server
RUN mkdir /var/run/sshd \
    && sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd \
    && echo "export VISIBLE=now" >> /etc/profile

# Change the initial root password
# !!!IMPORTANT: PASSWORD MUST BE CHANGED IMMIDIATELY AFTER FIRST LOGIN!!!
RUN echo 'root:nehezjelszo' | chpasswd

# Create user to use at SSH connection
# !!!IMPORTANT: PASSWORD MUST BE CHANGED IMMIDIATELY AFTER FIRST LOGIN!!!
RUN groupadd data-collector-users \
    && useradd -G data-collector-users -s /bin/bash -m data-collector-user \
    && echo 'data-collector-user:nehezjelszo' | chpasswd

############## INSTALL APPLICATION ################

# Install app
RUN mkdir /app /data
COPY . /app
RUN cd /app && make install

EXPOSE 22

CMD ["/usr/bin/supervisord", "-nu", "root", "-c", "/app/docker/supervisord.conf"]