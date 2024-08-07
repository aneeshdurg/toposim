import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .topology import Node, Topology
from .utils import print_to_file, print_to_script


appdata_dir = Path(__file__).parent / "appdata"


class Application(ABC):
    @abstractmethod
    def initialize(self, topo: Topology):
        pass

    @abstractmethod
    def image(self, node: Node) -> str:
        pass

    @abstractmethod
    def volumes(self, node: Node) -> dict[str, str]:
        pass

    @abstractmethod
    def environment(self) -> Optional[dict[str, str]]:
        pass

    @abstractmethod
    def entrypoint(self, node: Node) -> Optional[str]:
        pass

    @abstractmethod
    def mem_limit(self, node: Node) -> Optional[str]:
        pass

    @abstractmethod
    def cpus(self, node: Node) -> Optional[float]:
        pass

    @abstractmethod
    def extra(self, topo: Topology):
        pass

    @abstractmethod
    def post_network_setup(self, topo: Topology, output):
        pass

    @abstractmethod
    def post_pause(self, output):
        pass


class JanusGraphOnCassandra(Application):
    def initialize(self, topo: Topology):
        # Seeds for cassandra
        self.seeds = list([k for k in topo.nodes.keys() if "client" not in k])[0]

    def image(self, node: Node) -> str:
        if "client" in node.name:
            return "janusgraph/janusgraph:latest"
        return "cassandra:3.11.8"

    def volumes(self, node: Node) -> dict[str, str]:
        if "client" in node.name:
            return {
                "../../mygraph": "/mygraph",
                "./graph.properties": "/opt/janusgraph/graph.properties",
            }
        return {
            f"./data/{node.name}": "/var/lib/cassandra",
            f"./etc/{node.name}": "/etc/cassandra",
            f"./wait.sh": "/wait.sh",
        }

    def environment(self) -> dict[str, str]:
        return {
            "CASSANDRA_SEEDS": f"{self.seeds}",
            "CASSANDRA_CLUSTER_NAME": "SolarSystem",
            "CASSANDRA_DC": "Mars",
            "CASSANDRA_RACK": "West",
            "CASSANDRA_ENDPOINT_SNITCH": "GossipingPropertyFileSnitch",
            "CASSANDRA_NUM_TOKENS": "128",
            "MAX_HEAP_SIZE": "2G",
            "HEAP_NEWSIZE": "400M",
        }

    def entrypoint(self, node: Node) -> Optional[str]:
        if node.is_dummy:
            return "bash -c true"
        if "client" not in node.name:
            return "bash ./wait.sh"
        return "sleep inf"

    def mem_limit(self, node: Node) -> Optional[str]:
        return "4g"

    def cpus(self, node: Node) -> Optional[float]:
        return None

    def extra(self, topo: Topology):
        shutil.copy(appdata_dir / "janusgraph/wait.sh", "wait.sh")

        os.makedirs("etc", exist_ok=True)
        try:
            for node in topo.nodes:
                shutil.copytree(
                    appdata_dir / "janusgraph/etc_template", f"./etc/{node}"
                )
        except Exception:
            pass

        with print_to_file("graph.properties") as output:
            output(f"storage.backend = cql")
            output(f"storage.hostname = {self.seeds}")
            output(f"storage.cql.local-datacenter = Mars")
            output(f"cluster.max-partitions = {(len(topo.nodes) - 1) * 2}")
            output(f"ids.placement = simple")

    def post_network_setup(self, topo: Topology, output):
        for n in topo.nodes:
            output(f"docker exec -u root {n} touch /etc/cassandra/done &")

    def post_pause(self, output):
        output(f"sudo rm -rf etc/**/done")


class TigerGraph(Application):
    def __init__(self, license=None):
        if license is None:
            self.license = appdata_dir / "tigergraph/license"
        else:
            self.license = license

    def initialize(self, topo: Topology):
        pass

    def image(self, node: Node) -> str:
        return "tigergraph/tigergraph:latest"

    def volumes(self, node: Node) -> dict[str, str]:
        return {"./data": "/home/tigergraph/data"}

    def environment(self) -> Optional[dict[str, str]]:
        return None

    def entrypoint(self, node: Node) -> Optional[str]:
        return None

    def mem_limit(self, node: Node) -> Optional[str]:
        return "8g"

    def cpus(self, node: Node) -> Optional[float]:
        return 2

    def extra(self, topo: Topology):
        try:
            os.mkdir("data")
        except FileExistsError:
            pass

        shutil.copy(appdata_dir / "tigergraph/setup-tg.sh", "data/setup-tg.sh")
        shutil.copy(self.license, "data/license")
        with print_to_script("setup-cluster.sh") as output:
            node_names = list(topo.nodes.keys())
            for name in node_names:
                output(
                    f"docker exec {name} bash -i -c '/home/tigergraph/data/setup-tg.sh' &"
                )
            output(f"wait")
            output()
            # It needs to wait for the GSQL service to be ready before
            # clustering
            output("get_gsql_status() {")
            output(
                "  docker exec $1 bash -i -c 'gadmin status gsql' | grep GSQL | awk '{print $4}'"
            )
            output("}")
            output("sleep_till_online() {")
            output("  local status=$(get_gsql_status $1)")
            output('  while [ "$status" != "Online" ]; do')
            output("    sleep 60")
            output("    status=$(get_gsql_status $1)")
            output("  done")
            output("  echo $1 is online!")
            output("}")
            for name in node_names:
                output(f"sleep_till_online {name} &")
            output("wait")
            output()

            new_config = []
            for i, node in enumerate(node_names):
                if i == 0:
                    continue
                name = f"m{i + 1}"
                new_config.append(f"{name}:{topo.nodes[node].ip}")

            num_replicas = 1

            output(
                f'docker exec {node_names[0]} bash -i -c \'gadmin cluster expand -y {",".join(new_config)} --ha {num_replicas}\''
            )

    def post_network_setup(self, topo: Topology, output):
        pass

    def post_pause(self, output):
        pass


class Galois(Application):
    def initialize(self, topo: Topology):
        pass

    def image(self, node: Node) -> str:
        return "galois"

    def volumes(self, node: Node) -> dict[str, str]:
        return {"./data": "/data"}

    def environment(self) -> Optional[dict[str, str]]:
        return None

    def entrypoint(self, node: Node) -> Optional[str]:
        return None

    def mem_limit(self, node: Node) -> Optional[str]:
        return None

    def cpus(self, node: Node) -> Optional[float]:
        return None

    def extra(self, topo: Topology):
        with open("data/hostfile", "w") as f:
            for node in topo.nodes.values():
                f.write(node.ip + "\n")

    def post_network_setup(self, topo: Topology, output):
        pass

    def post_pause(self, output):
        pass

