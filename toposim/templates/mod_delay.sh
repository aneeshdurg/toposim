set -x
# Usage ./mod_delay <delay in ms>
# note that add_delay must be run at least once

{% include 'run_in_ns_fn.sh' %}

{%- for p in topo.ports.values() +%}
  {%- for i in range(p.networks | length) +%}
run_in_ns {{p.name}} tc qdisc change dev eth{{i}} root netem delay $1ms &
  {%- endfor %}
{%- endfor %}
wait"
