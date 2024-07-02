#!/bin/bash

# Function to run a command in the network namespace of a container
run_in_ns() {
  pid=$(docker inspect "$1" | jq -r '.[0].State.Pid')
  shift
  flag="-n"
  # if $1 starts with a -, then replace $flag with $1
  if [[ $1 == -* ]]; then
      flag=$1
      shift
  fi
  sudo nsenter -t $pid $flag "$@"
}

# Check if at least 2 arguments are provided
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <container_name> <command> [args...]"
  exit 1
fi

container=$(docker ps --filter "name=$1" --format "{{.Names}}")

if [ -z "$container" ]; then
  echo "Error: No container found with name $1"
  exit 1
fi

run_in_ns "$container" "${@:2}"
