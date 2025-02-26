set -x

# Setup networking using the topology specified to construct a static routing
# table.

{% include 'run_in_ns_fn.sh' %}

# Parse arguments
parser=$({
  argparsh new $0
  argparsh add_arg --action store_true --helptext "Directly execute commands for the current host" -- "--cloudlab"
})

eval $(argparsh parse $parser --format assoc-array --name args -- "$@")

if [ "${args["cloudlab"]}" == "True" ]; then
  # If we're deploying the network in cloudlab, then we only want to set routes
  # on this host. We redefine `run_in_ns` to ignore all commands that run in
  # "namespaces" (hosts) that aren't the host executing this script, and
  # directly execute commands within this "namespace" to set routes.
  run_in_ns() {
    local tgt_hostname=$1
    local my_hostname=$(hostname)
    shift
    if [ "$tgt_hostname" == "$my_hostname" ]; then
      "$@"
    fi
  }
fi


# Enables forwarding on a particular interface for a given host
#   $1 = namespace to run in
#   $2 = interface to forward on
forward() {
  run_in_ns $1 iptables -t nat -A POSTROUTING --out-interface $2 -j ACCEPT
  run_in_ns $1 iptables -A FORWARD -o $2 -j ACCEPT
}

# Given a subnet, find the interface with an IP matching the input subnet
#   $1 = namespace to run in
#   $2 = subnet
get_iface_for_subnet() {
  run_in_ns $1 ip addr | grep "inet $2\." | awk '{ print $NF }'
}

# for every port, set up packet forwarding
{%- for p in topo.ports.values() +%}
  {%- for i in range(p.networks | length) +%}
forward {{p.name}} eth{{i}}
  {%- endfor %}
{%- endfor %}

# for every node forward subnet/16 to the port
{%- for n in topo.nodes +%}
setup_{{n}}() {
  {%- for m in topo.nodes if n != m +%}
      {%- set subnet = topo.nodes[m].networks[0].subnet16 %}
  run_in_ns {{n}} ip route add {{subnet}}.0.0/16 via {{topo.ports[n].ips[0]}} dev eth0
  {%- endfor %}
}
setup_{{n}} &
{%- endfor %}

wait

# for every port setup routes according to the routing table
{%- for (n, p) in topo.ports.items() +%}
setup_{{p.name}}() {
  {%- for dst in topo.link_to_network[n] +%}
    {%- set target_net = topo.link_to_network[n][dst] -%}
    {%- set forward_net = topo.ports[dst].networks[0].subnet16 + ".0.0/16" -%}
    {#- need to resolve ??? by getting the ip of the other port on the network... -#}
    {%- set forward_ip = topo.link_to_fwd_ip[n][dst] -%}
    {%- set link_subnet = forward_ip.rsplit(".", 2)[0] %}
  iface=$(get_iface_for_subnet {{p.name}} {{link_subnet}})
  run_in_ns {{p.name}} ip route add {{forward_net}} via {{forward_ip}} dev $iface
  {%- endfor %}
}
setup_{{p.name}} &
{%- endfor %}
wait

# Output a mapping from each link to the interface it's assigned to
echo > links.yml
{%- for n in topo.nodes +%}
echo {{n}}: >> links.yml
{%- set port = topo.ports[n] -%}
{%- set network = topo.nodes[n].networks[0] %}
echo '  '{{port.name}}: >> links.yml
echo '    - '$(get_iface_for_subnet {{n}} {{network.subnet16}}) >> links.yml
{%- endfor %}

{%- for (n, p) in topo.ports.items() +%}
echo {{p.name}}: >> links.yml
    {%- set node_net = p.networks[0] %}
echo '  '{{n}}: >> links.yml
echo '    - '$(get_iface_for_subnet {{p.name}} {{node_net.subnet16}}) >> links.yml
  {%- for net in p.networks[1:] +%}
    {#- {% set found = False %} -#}
    {%- for q in topo.ports.values() if p != q +%}
      {%- if net in q.networks +%}
        {#- {% set found = True %} #}
echo '  '{{q.name}}: >> links.yml
echo '    - '$(get_iface_for_subnet {{p.name}} {{net.subnet16}}) >> links.yml
      {%- endif %}
      {#- assert found, "need to search nodes also?" -#}
    {%- endfor %}
  {%- endfor %}
{%- endfor %}
