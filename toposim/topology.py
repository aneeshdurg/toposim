import sys
from dataclasses import dataclass, field


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

    def vend_ip(self) -> str:
        ip = f"{self.subnet16}.0.{self._counter}"
        self._counter += 1
        return ip


@dataclass
class Port:
    prefix: str
    id_: int
    networks: list[Network] = field(default_factory=lambda: [])
    ip: list[str] = field(default_factory=lambda: [])

    @property
    def name(self) -> str:
        return f"{self.prefix}_port{self.id_}"


@dataclass
class Node:
    name: str
    links: list[str]
    # node to interface to communicate on (every node get it's own subnet)
    routes: dict[str, int] = field(default_factory=lambda: {})
    networks: list[Network] = field(default_factory=lambda: [])
    ip: str = ""


class Topology:
    nodes: dict[str, Node]
    ports: dict[str, Port]
    # [n1, n2] -> net
    link_to_network: dict[str, dict[str, Network]]
    # [n1, n2] -> ip n1 should forward traffic to to reach n2
    link_to_fwd_ip: dict[str, dict[str, str]]
    networks: list[Network]

    _subnet = 1
    _subnet32 = "174"

    def create_network(self) -> Network:
        global _subnet
        res = Network(f"net{self._subnet}", f"{self._subnet32}.{self._subnet}")
        self.networks.append(res)
        self._subnet += 1
        return res

    def build_routing_table(self) -> dict[str, dict[str, str]]:
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

    def __init__(self, prefix: str, nodes: dict[str, Node]):
        self.networks = []
        self.nodes = nodes

        routes = self.build_routing_table()
        for name, r in routes.items():
            log(name, r)

        ports = {}
        for i, n in enumerate(nodes):
            ports[n] = Port(prefix, i)

        num_networks = sum(len(n.links) for n in nodes.values()) // 2
        log(f"Requires {num_networks} networks between ports")

        for n in nodes:
            net = self.create_network()
            nodes[n].networks.append(net)
            nodes[n].ip = net.vend_ip()
            ports[n].networks.append(net)
            ports[n].ip.append(net.vend_ip())

        unique_links = set()
        for n in nodes.values():
            for l in n.links:
                if (l, n.name) in unique_links:
                    continue
                unique_links.add((n.name, l))

        link_to_network = {n: {} for n in nodes}
        link_to_fwd_ip = {n: {} for n in nodes}
        for node1, node2 in unique_links:
            net = self.create_network()
            ports[node1].networks.append(net)
            ports[node1].ip.append(net.vend_ip())
            ports[node2].networks.append(net)
            ports[node2].ip.append(net.vend_ip())

            link_to_network[node1][node2] = net
            link_to_fwd_ip[node1][node2] = ports[node2].ip[-1]
            link_to_network[node2][node1] = net
            link_to_fwd_ip[node2][node1] = ports[node1].ip[-1]

        for src in routes:
            for dst in routes[src]:
                if routes[src][dst] == dst:
                    continue
                link_to_network[src][dst] = link_to_network[src][routes[src][dst]]
                link_to_fwd_ip[src][dst] = link_to_fwd_ip[src][routes[src][dst]]

        self.ports = ports
        self.link_to_network = link_to_network
        self.link_to_fwd_ip = link_to_fwd_ip
        print(link_to_network)
