# Get the MAC address of every node

{% include 'run_in_ns_fn.sh' %}

get_mac() {
  run_in_ns $1 ip link show eth0 | grep link/ether | awk '{print $2}'
}

{%- for n in topo.nodes +%}
echo {{n}} $(get_mac {{n}})
{%- endfor %}
