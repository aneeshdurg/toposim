# Add a constant delay to every packet sent over the network. See mod_delay for
# a customizable delay
set -x

{% include 'run_in_ns_fn.sh' %}

{%- for p in topo.ports.values() +%}
  {%- for i in range(p.networks | length) +%}
run_in_ns {{p.name}} tc qdisc add dev eth{{i}} root netem delay 25ms &
  {%- endfor %}
{%- endfor %}
wait"
