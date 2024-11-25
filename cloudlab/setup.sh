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

cd ~

# Create the cluster from the config
~/.local/bin/toposim cluster /toposim/toposim-main/cloudlab/config.json

# Setup ssh access between all hosts using the same key
mkdir -p ~/.ssh
cp /toposim/toposim-main/cloudlab/id_ecdsa* ~/.ssh/
chmod 600 ~/.ssh/id_ecdsa*
cat .ssh/id_ecdsa.pub >> .ssh/authorized_keys

install_dummy() {
  true
}

install_compute() {
  setup_docker
}

if [ "${args["dummy"]}" == "True" ]; then
  install_dummy
else
  install_compute
fi

# Run a cloudlab specific setup script if it exists
setup_script=./cluster/cloudlab_setup.sh
[ -e $setup_script ] && $setup_script
