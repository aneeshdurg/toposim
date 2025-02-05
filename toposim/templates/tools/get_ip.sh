# Get the MAC address of every node

{% include 'run_in_ns_fn.sh' %}

get_ip() {
  run_in_ns $1 ip address show eth0 | grep 'inet ' | awk '{print $2}'
}

{%- for n in topo.nodes +%}
echo {{n}} $(get_ip {{n}})
{%- endfor %}
