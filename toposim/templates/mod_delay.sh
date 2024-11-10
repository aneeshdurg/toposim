set -x
# note that add_delay must be run at least once

parser=$({
  argparsh new $0 -d "Modify delay on network interfaces"
  argparsh add_arg "delay" -- --type int
})
eval $(argparsh parse $parser -- "$@")

{% include 'run_in_ns_fn.sh' %}

{%- for p in topo.ports.values() +%}
  {%- for i in range(p.networks | length) +%}
run_in_ns {{p.name}} tc qdisc change dev eth{{i}} root netem delay ${delay}ms &
  {%- endfor %}
{%- endfor %}
wait"
