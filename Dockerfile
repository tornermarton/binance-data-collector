FROM ubuntu:latest
MAINTAINER tornermarton

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

WORKDIR /

# Install system packages
RUN apt -q update --fix-missing

# Remove login messages
RUN chmod -x /etc/update-motd.d/*

# Configure ssh server
RUN apt -q install -y openssh-server
RUN mkdir /var/run/sshd \
    && sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd \
    && echo "export VISIBLE=now" >> /etc/profile
ENV NOTVISIBLE "in users profile"

# Change the initial root password
# !!!IMPORTANT: PASSWORD MUST BE CHANGED IMMIDIATELY AFTER FIRST LOGIN!!!
RUN echo 'root:nehezjelszo' | chpasswd

# Install supervisord and copy configurations
RUN apt -q install -y openssh-server supervisor
COPY /docker/supervisor/ /etc/supervisor/conf.d/

# Create user to use at SSH connection
# !!!IMPORTANT: PASSWORD MUST BE CHANGED IMMIDIATELY AFTER FIRST LOGIN!!!
RUN groupadd data-collector-users \
    && useradd -G data-collector-users -s /bin/bash -m data-collector-user \
    && echo 'data-collector-user:nehezjelszo' | chpasswd

# Cleanup
RUN apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Install app
RUN mkdir /app
COPY . /app
RUN make install

USER data-collector-user

COPY docker/configs.json /configs.json

# Attach persistent volume to /data on container
RUN mkdir /data

EXPOSE 22

CMD ["/usr/bin/supervisord"]