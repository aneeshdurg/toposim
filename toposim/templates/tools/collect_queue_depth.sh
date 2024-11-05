# Collect queue depth at specified intervals

{% include 'run_in_ns_fn.sh' %}

PIDFILE=${TMPDIR:-/tmp}/collect_queue_depth_pid
start_collection() {
  local interval=$1

  echo $$ > $PIDFILE
  while true; do
{%- for n in topo.nodes +%}
  run_in_ns {{n}} tc -s -d qdisc ls dev eth0
{%- endfor %}
    sleep $interval
  done
}

stop_collection() {
  kill -SIGKILL $(cat $PIDFILE)
}

usage() {
  echo "Usage: $0 {start | stop} [collection_interval_s]"
  exit 1
}

# Prompt for sudo password
sudo true

# Main script logic
case "$1" in
  start)
    [ $# -eq 2 ] || usage
    start_collection $2
    ;;
  stop)
    stop_collection
    ;;
  *)
    usage
    ;;
esac
