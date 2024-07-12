set -x

{% include 'run_in_ns_fn.sh' %}

forward() {
  run_in_ns $1 iptables -t nat -A POSTROUTING --out-interface $2 -j MASQUERADE
  run_in_ns $1 iptables -A FORWARD -o $2 -j ACCEPT
}

get_iface_for_subnet() {
  run_in_ns $1 ip addr \
    | grep "inet $2" -B2 | head -n1 | cut -d\\  -f2 | cut -d@ -f1
}

# for every port, set up packet forwarding
{%-  for p in topo.ports.values() +%}
  {%- for i in range(p.networks | length) +%}
forward {{p.name}} eth{{i}}
  {%- endfor %}
{%- endfor %}

# for every node forward subnet/16 to the port
for n in topo.nodes:
    output(f"setup_{n}() {{")
    for m in topo.nodes:
        if n == m:
            continue
        subnet = topo.nodes[m].networks[0].subnet16
        output("  ", end="")
        run_in_ns(
            n,
            f"ip route add {subnet}.0.0/16 via {topo.ports[n].ips[0]} dev eth0",
        )
    output("}")
    output(f"setup_{n} &")
output("wait")
output()

# for every port setup routes according to the routing table
for n, p in topo.ports.items():
    output(f"setup_{p.name}() {{")
    for dst in topo.link_to_network[n]:
        target_net = topo.link_to_network[n][dst]
        forward_net = f"{topo.ports[dst].networks[0].subnet16}.0.0/16"
        # need to resolve ??? by getting the ip of the other port on the
        # network...
        forward_ip = topo.link_to_fwd_ip[n][dst]
        link_subnet = forward_ip.rsplit(".", 2)[0]
        output(f"  iface=$(get_iface_for_subnet {p.name} {link_subnet})")
        output("  ", end="")
        run_in_ns(
            p.name, f"ip route add {forward_net} via {forward_ip} dev $iface"
        )
    output("}")
    output(f"setup_{p.name} &")
output("wait")
output()

# Output a mapping from each link to the interface it's assigned to
output("echo > links.yml")
{%- for n in topo.nodes +%}
echo {{n}}: >> links.yml
{% set port = topo.ports[n] %}
{% set network = topo.nodes[n].networks[0] %}
echo ' ' {{port.name}}: $(get_iface_for_subnet {{n}} {{network.subnet16}}) >> links.yml
{%- endfor %}

for n, p in topo.ports.items():
    output(f"echo {p.name}: >> links.yml")
    node_net = p.networks[0]
    output(
        f"echo ' ' {n}: $(get_iface_for_subnet {p.name} {node_net.subnet16}) >> links.yml"
    )
    for net in p.networks[1:]:
        found = False
        for q in topo.ports.values():
            if p == q:
                continue
            if net in q.networks:
                found = True
                get_net = f"$(get_iface_for_subnet {p.name} {net.subnet16})"
                output(f"echo ' ' {q.name}: {get_net} >> links.yml")
        assert found, "need to search nodes also?"

app.post_network_setup(topo, output)
output("wait")
