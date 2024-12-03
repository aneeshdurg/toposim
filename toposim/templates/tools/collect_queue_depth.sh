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

parser=$({
  argparsh new $0 -d "Collect queue depth during workload"
  argparsh add_subparser command --required

  argparsh add_subcommand start
  argparsh set_defaults --subcommand start --command start_collection
  argparsh add_subcommand stop
  argparsh set_defaults --subcommand stop --command stop_collection

  argparsh add_arg --subcommand start "outdir"
  argparsh add_arg --subcommand start --type int --default 1 -- -i --interval
})
eval $(argparsh parse $parser --format assoc-array --name args_ -- "$@")

# Prompt for sudo password
sudo true

${args_["command"]} args_ &
childpid=$!

if [ "${args_["command"]}" == "start_collection" ]; then
  # Save the background proc id
  echo "started collection with PID" $childpid
  echo $childpid > $PIDFILE
else
  wait
fi
