# Collect queue depth at specified intervals

{% include 'run_in_ns_fn.sh' %}

PIDFILE=${TMPDIR:-/tmp}/collect_queue_depth_pid
start_collection() {
  local -n args=$1
  echo "saving results to" ${args["outdir"]}
  mkdir -p ${args["outdir"]}
  while true; do
{%- for n in topo.nodes +%}
  run_in_ns {{n}} tc -s -d qdisc ls dev eth0 >> ${args["outdir"]}/{{n}}.txt
{%- endfor %}
    sleep ${args["interval"]}
  done
}

stop_collection() {
  kill -SIGKILL $(cat $PIDFILE)
}

usage() {
  echo "Usage: $0 {start | stop} [collection_interval_s]"
  exit 1
}

set -e
parser=$({
  argparsh new $0 -d "Collect queue depth during workload"
  argparsh subparser_init --required true --metaname command

  argparsh subparser_add start
  argparsh subparser_add stop

  argparsh add_arg --subparser start "outdir"
  argparsh add_arg --subparse start -i --interval -- --type int --default 1
})
eval $(argparsh parse $parser --format assoc_array --name args_ -- "$@")
set +e

# Prompt for sudo password
sudo true

eval "${args_["command"]}_collection args_ &"
childpid=$!

if [ "${args_["command"]}" == "start" ]; then
  # Save the background proc id
  echo "started collection with PID" $childpid
  echo $childpid > $PIDFILE
else
  wait
fi