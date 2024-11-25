import sys
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Union


def log(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


# Given a list of nodes, we need to create a unique forwarding node to simplify
# accounting for traffic and setting delays. E.g. to model:
#      (A)
#       |
#   +---+---+
#   |       |
#  (B)     (C)
#   |
#  (D)
#
# We actually create:
#     (A)-(1)
#          |
#      +---+---+
#      |       |
# (B)-(2)     (3)-(C)
#      |
# (D)-(4)


@dataclass
class Network:
    name: str
    subnet16: str
    _counter: int = 2
    devices: Dict[str, str] = field(default_factory=lambda: {})

    def vend_ip(self) -> str:
        ip = f"{self.subnet16}.0.{self._counter}"
        self._counter += 1
        return ip

    def add_dev(self, device: Union["Port", "Node"]):
        ip = device.attach(self)
        self.devices[device.name] = ip


@dataclass
class Port:
    name: str
    networks: List[Network] = field(default_factory=lambda: [])
    ips: List[str] = field(default_factory=lambda: [])

    def attach(self, net: Network) -> str:
        self.networks.append(net)
        ip = net.vend_ip()
        self.ips.append(ip)
        return ip


@dataclass
class Node:
    name: str
    links: List[str]
    is_dummy: bool
    # node to interface to communicate on (every node get it's own subnet)
    routes: Dict[str, int] = field(default_factory=lambda: {})
    networks: List[Network] = field(default_factory=lambda: [])
    ip: str = ""

    def attach(self, net: Network) -> str:
        assert self.ip == ""
        self.networks.append(net)
        self.ip = net.vend_ip()
        return self.ip


class Topology:
    prefix: str
    nodes: Dict[str, Node]
    dummies: Dict[str, Node]
    ports: Dict[str, Port]
    # [n1, n2] -> net
    link_to_network: Dict[str, Dict[str, Network]]
    # [n1, n2] -> ip n1 should forward traffic to to reach n2
    link_to_fwd_ip: Dict[str, Dict[str, str]]
    networks: List[Network]

    _subnet32: str
    _subnet = 1

    def create_network(self) -> Network:
        global _subnet
        res = Network(f"net{self._subnet}", f"{self._subnet32}.{self._subnet}")
        self.networks.append(res)
        self._subnet += 1
        return res

    def build_routing_table(self) -> Dict[str, Dict[str, str]]:
        route_table = {n: {} for n in self.nodes}
        messages = {n: [[]] for n in self.nodes}
        while any(len(r) != (len(self.nodes) - 1) for r in route_table.values()):
            # propogate all messages
            new_messages = {}
            for name, routes in messages.items():
                new_routes = []
                node = self.nodes[name]
                for r in routes:
                    if len(r):
                        dst = r[-1]
                        if dst != name and dst not in route_table[name]:
                            route_table[name][dst] = r[0]
                    new_routes.append([name] + r)
                for l in node.links:
                    if l not in new_messages:
                        new_messages[l] = []
                    new_messages[l] += new_routes
            messages = new_messages
        return route_table

    def __init__(self, prefix: str, nodes: Dict[str, Node], subnet32: str = "174"):
        self.prefix = prefix
        self.networks = []
        self.nodes = nodes
        self.dummies = {}
        self._subnet32 = subnet32

        routes = self.build_routing_table()
        for name, r in routes.items():
            log(name, r)

        ports: Dict[str, Port] = {}
        for i, n in enumerate(nodes):
            if nodes[n].is_dummy:
                ports[n] = Port(n)
            else:
                ports[n] = Port(f"{prefix}_port{i}")

        num_networks = sum(len(n.links) for n in nodes.values()) // 2
        log(f"Requires {num_networks} networks between ports")

        for n in nodes:
            net = self.create_network()
            net.add_dev(nodes[n])
            net.add_dev(ports[n])

        unique_links: Set[Tuple[str, str]] = set()
        for n in nodes.values():
            for l in n.links:
                if (l, n.name) in unique_links:
                    continue
                unique_links.add((n.name, l))

        link_to_network: Dict[str, Dict[str, Network]] = {n: {} for n in nodes}
        link_to_fwd_ip: Dict[str, Dict[str, str]] = {n: {} for n in nodes}
        for node1, node2 in unique_links:
            net = self.create_network()
            net.add_dev(ports[node1])
            net.add_dev(ports[node2])

            link_to_network[node1][node2] = net
            link_to_fwd_ip[node1][node2] = ports[node2].ips[-1]
            link_to_network[node2][node1] = net
            link_to_fwd_ip[node2][node1] = ports[node1].ips[-1]

        for src in routes:
            for dst in routes[src]:
                if routes[src][dst] == dst:
                    continue
                link_to_network[src][dst] = link_to_network[src][routes[src][dst]]
                link_to_fwd_ip[src][dst] = link_to_fwd_ip[src][routes[src][dst]]

        self.ports = ports
        self.link_to_network = link_to_network
        self.link_to_fwd_ip = link_to_fwd_ip

        dummies = [n for n in self.nodes if self.nodes[n].is_dummy]
        for d in dummies:
            self.dummies[d] = self.nodes[d]
            del self.nodes[d]
