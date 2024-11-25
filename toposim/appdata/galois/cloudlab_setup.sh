#!/usr/bin/env bash
set -e

parser=$({
  argparsh new $0
  argparsh add_arg "toposimdir"
})

eval $(argparsh parse $parser --format assoc-array --name args -- "$@")

pushd ${args["toposimdir"]}/toposim/appdata/galois
sudo docker build -t galois .
popd
