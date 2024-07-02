#!/bin/bash
set -x

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

# Function to start tcpdump on all interfaces in matching containers
start_tcpdump() {
  for container in $(docker ps --filter "name=${PREFIX}[0-9]+" --format "{{.Names}}"); do
    # Define the output file path in the container

    for iface in $(run_in_ns $container ip addr | grep inet | grep eth | rev | cut -d\  -f 1 | rev); do
      container_output_file="/mnt/dhwang/tcpdump_outputs/dumpfile_${container}_${iface}.pcap"
      # Start tcpdump
      run_in_ns $container tcpdump -e -i $iface -w $container_output_file &
    done
  done
}

# Function to stop all tcpdump processes in matching containers and copy output to the host
stop_tcpdump() {
  # This will kill ALL tcpdump processes - so make sure you're not running any
  # tcpdump instances that weren't started by this script.
  sudo pkill tcpdump
}

sudo true

# Main script logic
case "$1" in
  start)
    start_tcpdump
    ;;
  stop)
    stop_tcpdump
    ;;
  *)
    echo "Usage: $0 {start|stop}"
    exit 1
    ;;
esac