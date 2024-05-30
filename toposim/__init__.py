#!/usr/bin/env python
import json
import os
import shutil
import sys
from pathlib import Path

from .application import Application
from .topology import Node, Topology
from .utils import print_to_file, print_to_script


def generate(prefix: str, filename: str, app: Application):
    with open(filename) as f:
        data = json.load(f)
    os.makedirs(prefix, exist_ok=True)
    os.chdir(prefix)

    names = set(data.keys())
    nodes = {}
    i = 0
    for k, links in data.items():
        for l in links:
            if l not in names:
                raise Exception(f"Unknown node {l}")
            assert k in data[l], f"malformed link {k} -> {l}"
        name = f"{prefix}_{k}"
        nodes[name] = Node(name, [f"{prefix}_{l}" for l in links])
        i += 1

    topo = Topology(prefix, nodes)

    app.initialize(topo)
    # Set up docker-compose.yml
    with print_to_file("docker-compose.yml") as output:
        output('version: "2.4"')
        output("networks:")
        for net in topo.networks:
            output(f"  {net.name}:")
            output(f"    driver: bridge")
            output(f"    ipam:")
            output(f"      config:")
            output(f"        - subnet: {net.subnet16}.0.0/16")
            output(f"          gateway: {net.subnet16}.0.1")
        output("services:")
        for p in topo.ports.values():
            output(f"  {p.name}:")
            output(f"    image: ubuntu:latest")
            output(f'    entrypoint: /bin/sh -c "sleep inf"')
            output(f"    container_name: {p.name}")
            output(f"    hostname: {p.name}")
            output(f"    cap_add:")
            output(f'      - "NET_ADMIN"')
            output(f"    networks:")
            for i, net in enumerate(p.networks):
                output(f"      {net.name}:")
                output(f"        ipv4_address: {p.ip[i]}")

        for i, node in enumerate(topo.nodes.values()):
            output(f"  {node.name}:")
            output(f"    image: {app.image(node)}")
            output(f"    container_name: {node.name}")
            output(f"    hostname: {node.name}")
            if mem_limit := app.mem_limit(node):
                output(f"    mem_limit: {mem_limit}")
            if entrypt := app.entrypoint(node):
                output(f"    entrypoint: {entrypt}")
            output(f"    networks:")
            output(f"      {node.networks[0].name}:")
            output(f"        ipv4_address: {node.ip}")
            output(f"    cap_add:")
            output(f'      - "NET_ADMIN"')
            output(f"    volumes:")
            for src, dst in app.volumes(node).items():
                output(f"      - {src}:{dst}")
            if env := app.environment():
                output(f"    environment: &environment")
                for key, val in env.items():
                    output(f'      {key}: "{val}"')

    app.extra(topo)

    # setup networking
    with print_to_script("setup-networking.sh") as output:
        output("set -x")
        output("run_in_ns() {")
        output("  pid=$(docker inspect $1 | jq \\.[0].State.Pid)")
        output("  shift")
        output('  flag="-n"')
        output("  # if $1 starts with a -, then replace $flag with $1")
        output("  if [[ $1 == -* ]]; then")
        output("      flag=$1")
        output("      shift")
        output("  fi")
        output('  sudo nsenter -t $pid $flag "$@"')
        output("}")
        output()

        def run_in_ns(name, cmd):
            output("run_in_ns", name, cmd)

        output("forward() {")
        output("  ", end="")
        run_in_ns(
            "$1", "iptables -t nat -A POSTROUTING --out-interface $2 -j MASQUERADE"
        )
        output("  ", end="")
        run_in_ns("$1", f"iptables -A FORWARD -o $2 -j ACCEPT")
        output("}")
        output()

        output("get_iface_for_subnet() {")
        output("  ", end="")
        run_in_ns(
            "$1",
            'ip addr | grep "inet $2" -B2 | head -n1 | cut -d\\  -f2 | cut -d@ -f1',
        )
        output()
        output("}")
        output()

        def forward(name, iface):
            output(f"forward {name} {iface}")

        # for every port, set up packet forwarding
        for p in topo.ports.values():
            for i in range(len(p.networks)):
                forward(p.name, f"eth{i}")
        output()
        # for every node forward 172.0.0.0/32 to the port
        for n in topo.nodes:
            output(f"setup_{n}() {{")
            for m in topo.nodes:
                if n == m:
                    continue
                subnet = topo.nodes[m].networks[0].subnet16
                output("  ", end="")
                run_in_ns(
                    n,
                    f"ip route add {subnet}.0.0/16 via {topo.ports[n].ip[0]} dev eth0",
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
                forward_net = f"{topo.nodes[dst].networks[0].subnet16}.0.0/16"
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

        app.post_network_setup(topo, output)
        output("wait")

    with print_to_script("add_delay.sh") as output:
        output("set -x")
        output("run_in_ns() {")
        output("  pid=$(docker inspect $1 | jq \\.[0].State.Pid)")
        output("  shift")
        output('  flag="-n"')
        output("  # if $1 starts with a -, then replace $flag with $1")
        output("  if [[ $1 == -* ]]; then")
        output("      flag=$1")
        output("      shift")
        output("  fi")
        output('  sudo nsenter -t $pid $flag "$@"')
        output("}")
        output()

        def run_in_ns(name, cmd):
            output("run_in_ns", name, cmd)

        # tc qdisc add dev eth0 root netem delay 2ms
        for p in topo.ports.values():
            for i in range(len(p.networks)):
                run_in_ns(p.name, f"tc qdisc add dev eth{i} root netem delay 25ms &")
        output("wait")
        output()

    with print_to_script("mod_delay.sh") as output:
        # Usage ./mod_delay.sh <delay in ms>
        # note that add_delay must be run at least once
        output("set -x")
        output("run_in_ns() {")
        output("  pid=$(docker inspect $1 | jq \\.[0].State.Pid)")
        output("  shift")
        output('  flag="-n"')
        output("  # if $1 starts with a -, then replace $flag with $1")
        output("  if [[ $1 == -* ]]; then")
        output("      flag=$1")
        output("      shift")
        output("  fi")
        output('  sudo nsenter -t $pid $flag "$@"')
        output("}")
        output()

        def run_in_ns(name, cmd):
            output("run_in_ns", name, cmd)

        for p in topo.ports.values():
            for i in range(len(p.networks)):
                run_in_ns(p.name, f"tc qdisc change dev eth{i} root netem delay $1ms &")
        output("wait")
        output()

    with print_to_script("cleanup.sh") as output:
        output("cleanup() {")
        output(f"  docker stop $1")
        output(f"  docker rm $1")
        output("}")
        output()

        for p in topo.ports.values():
            output(f"cleanup {p.name} &")
        for n in topo.nodes:
            output(f"cleanup {n} &")
        output("wait")
        output()

        for net in topo.networks:
            output(f"docker network rm {prefix}_{net.name}")

    with print_to_script("pause.sh") as output:
        for node in topo.nodes:
            output(f"docker stop {node} & ")
        for p in topo.ports.values():
            output(f"docker stop {p.name} &")
        output("wait")
        output()
        app.post_pause(output)

    with print_to_script("resume.sh") as output:
        for node in topo.nodes:
            output(f"docker start {node} &")
        for p in topo.ports.values():
            output(f"docker start {p.name} &")
        output("wait")
        output(f"sleep 5")
        output(f"./setup-networking.sh")
