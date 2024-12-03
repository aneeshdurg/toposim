# Run tcpdump on every interface in the cluster

{% include 'run_in_ns_fn.sh' %}

start_tcpdump() {
  local -n args=$1
  local output_dir="${args["outdir"]}"
  mkdir -p $output_dir

{%- for n in topo.nodes +%}
  output_file=$output_dir/{{n}}_eth0
  run_in_ns {{n}} tcpdump -e -i eth0 -w $output_file &
{%- endfor %}


{%- for p in topo.ports.values() +%}
  {%- for i in range(p.networks | length) +%}

  output_file=$output_dir/{{p.name}}_eth{{i}}
  run_in_ns {{p.name}} tcpdump -e -i eth{{i}} -w $output_file &
  {%- endfor %}
{%- endfor %}
}

stop_tcpdump() {
  # This will kill ALL tcpdump processes - so make sure you're not running any
  # tcpdump instances that weren't started by this script.
  # TODO - only kill process started by this script
  sudo pkill tcpdump
}

parser=$({
  argparsh new $0 -d "run tcpdump on all host interfaces"
  argparsh add_subparser command --required

  argparsh add_subcommand start
  argparsh set_defaults --subcommand start --command start_tcpdump
  argparsh add_arg --subcommand start "outdir"

  argparsh add_subcommand stop
  argparsh set_defaults --subcommand stop --command stop_tcpdump
})
eval $(argparsh parse $parser --format assoc-array --name args_ -- "$@")

sudo true
${args_["command"]} args_
