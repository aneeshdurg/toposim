FROM ubuntu:24.04

# Install conda code taken from https://stackoverflow.com/a/58269633/5803067
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"

# Install wget to fetch Miniconda
RUN apt-get update && \
    apt-get install -y wget git cmake build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Miniconda on x86 or ARM platforms
RUN arch=$(uname -m) && \
    if [ "$arch" = "x86_64" ]; then \
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"; \
    elif [ "$arch" = "aarch64" ]; then \
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"; \
    else \
    echo "Unsupported architecture: $arch"; \
    exit 1; \
    fi && \
    wget $MINICONDA_URL -O miniconda.sh && \
    mkdir -p /root/.conda && \
    bash miniconda.sh -b -p /root/miniconda3 && \
    rm -f miniconda.sh
RUN conda init

# Copy the environment into the container
COPY environment.yml .
# Install all deps
RUN conda install -c conda-forge -y mamba && \
  mamba env create -n Galois -f environment.yml
# Clone and build Galois with distributed enabled
RUN git clone https://github.com/IntelligentSoftwareSystems/Galois src
RUN mkdir Galois
RUN conda run -n Galois --no-capture-output \
    cmake -S src -B Galois/ -DCMAKE_BUILD_TYPE=Release -DGALOIS_ENABLE_DIST=1
RUN conda run -n Galois --no-capture-output make -C Galois/ -j $(nproc)
# Enable the galois envrionment by default
RUN echo "conda activate Galois" >> /root/.bashrc


RUN apt-get update && apt-get install -y openssh-server
RUN echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
RUN echo "PermitEmptyPasswords yes" >> /etc/ssh/sshd_config
RUN echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config
RUN passwd -d root

EXPOSE 22


RUN mkdir /run/sshd
CMD ["/usr/sbin/sshd", "-D"]
