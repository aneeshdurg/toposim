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

PREFIX="slimfly_3_.*"
declare -A ip_container_dict

for container in $(docker ps --filter "name=${PREFIX}[0-9]+" --format "{{.Names}}"); do
  while read -r line; do
    ip=$(echo $line | awk '{print $2}' | cut -d'/' -f1)
    ip_container_dict["$ip"]=$container
  done < <(run_in_ns $container ip a | grep "inet 174")
done

# Print the dictionary
for ip in "${!ip_container_dict[@]}"; do
  echo "\"$ip\":\"${ip_container_dict[$ip]}\","
done
