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
declare -A mac_container_dict

for container in $(docker ps --filter "name=${PREFIX}[0-9]+" --format "{{.Names}}"); do
  while read -r iface; do
    mac=$(run_in_ns $container ip link show "$iface" | grep "link/ether" | awk '{print $2}')
    mac_container_dict["$mac"]=$container
  done < <(run_in_ns $container ip -o a | grep "inet 174" | awk '{print $2}')
done

# Print the dictionary
for mac in "${!mac_container_dict[@]}"; do
  echo "\"$mac\":\"${mac_container_dict[$mac]}\","
done
