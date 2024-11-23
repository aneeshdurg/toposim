#!/usr/bin/env bash

# Create logfile and redirect all logs to the new fd
LOGS=/tmp/setuplogs.txt
touch $LOGS
exec 3<> $LOGS
exec 2>&3 1>&3

# Turn on logging and exit on error
set -ex

sudo apt-get update -y
sudo apt-get install -y python3-pip python3-dev
curl https://sh.rustup.rs -sSf | sh -s -- -y
. ~/.cargo/env

cargo install argparsh

parser=$({
  argparsh new $0
  argparsh add_arg "--dummy" -- --action store_true
  argparsh add_arg "--hostname" -- --required True
})

eval $(argparsh parse $parser --format assoc_array --name args -- "$@")

# We need --break-system-packages because we're not using a managed python
# environment
pip install /toposim/toposim-main/ --break-system-packages

# Verify that toposim was installed correctly
~/.local/bin/toposim --help

# Set the hostname
sudo hostnamectl set-hostname "${args["hostname"]}"

setup_docker() {
  # Add Docker's official GPG key:
  sudo apt-get install -y ca-certificates curl
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc

  # Add the repository to Apt sources:
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update -y

  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

# Install docker
# setup_docker

# Setup galois
# pushd /toposim/toposim-main/toposim/appdata/galois
# docker build -t galois .
# popd

# Create the cluster from the config
~/.local/bin/toposim cluster /toposim/toposim-main/cloudlab/config.json # --app galois

# Set up routing
./cluster/setup-networking --cloudlab

install_dummy() {
}

install_compute() {
  setup_docker
}

if [ "${args["dummy"]}" == "True" ]; then
  install_dummy
else
  install_compute
fi
