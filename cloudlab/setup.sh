#!/usr/bin/env bash
set -ex

LOGS=/tmp/setuplogs.txt
touch $LOGS
exec 2>&1 1>$LOGS

echo "ARGUMENTS"
echo "$@"

# Add Docker's official GPG key:
sudo apt-get update -y
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

sudo apt-get install -y python3-pip python3-dev
curl https://sh.rustup.rs -sSf | sh -s -- -y
. ~/.cargo/env

cargo install argparsh

# We need --break-system-packages because we're not using a managed python
# environment
pip install /toposim/toposim-main/ --break-system-packages

# Verify that toposim was installed correctly
~/.local/bin/toposim --help