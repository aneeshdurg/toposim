# Use Ubuntu 16.04 as the base image
FROM ubuntu:16.04

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && \
    apt-get install -y \
        gcc \
        g++ \
        build-essential \
        libopenmpi-dev \
        openmpi-bin \
        default-jdk \
        cmake \
        zlib1g-dev \
        git \
        python python3 \
        python-pip python3-pip \
        openssh-server \
        sudo \
    && apt-get clean
RUN pip install numpy==1.10.1

# Set the working directory
WORKDIR /sgp

USER root

# # ------------------------------------------------------------
# # Set up default user 
# # ------------------------------------------------------------

ARG USER=mpi
ENV USER ${USER}
RUN useradd -ms /bin/bash ${USER} \
      && echo "${USER}   ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

ENV USER_HOME /home/${USER}
RUN chown -R ${USER}:${USER} ${USER_HOME} &&\
    mkdir -p /var/run/sshd &&\
	chown -R ${USER}:${USER} /sgp &&\
	chmod -R 777 /sgp

# # ------------------------------------------------------------
# # Set up SSH Server 
# # ------------------------------------------------------------

# Add host keys
RUN cd /etc/ssh/ && ssh-keygen -A -N ''

# Config SSH Daemon
RUN echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
RUN echo "PermitEmptyPasswords yes" >> /etc/ssh/sshd_config
RUN echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config
RUN passwd -d root
 
# Set up user's public and private keys
ENV SSHDIR ${USER_HOME}/.ssh
RUN mkdir -p ${SSHDIR}

COPY ssh/ ${SSHDIR}/

RUN cat ${SSHDIR}/*.pub >> ${SSHDIR}/authorized_keys
RUN chmod -R 600 ${SSHDIR}/* \
         && chown -R ${USER}:${USER} ${SSHDIR}

# # Start SSH Server 
EXPOSE 22
RUN mkdir -p /var/run/sshd
CMD ["/usr/sbin/sshd", "-D"]