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
    def environment(self, node: Node) -> Optional[dict[str, str]]:
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
    def ports(self, node: Node) -> Optional[dict[str, str]]:
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

    def should_create_volumes(self) -> bool:
        return False

    def depends_on(self, node: Node) -> Optional[str]:
        return None

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

    def environment(self, node: Node) -> dict[str, str]:
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
    
    def ports(self, node: Node) -> Optional[dict[str, str]]:
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

    def environment(self, node: Node) -> Optional[dict[str, str]]:
        return None

    def entrypoint(self, node: Node) -> Optional[str]:
        return None

    def mem_limit(self, node: Node) -> Optional[str]:
        return "8g"

    def cpus(self, node: Node) -> Optional[float]:
        return 2
    
    def ports(self, node: Node) -> Optional[dict[str, str]]:
        return None

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

    def environment(self, node: Node) -> Optional[dict[str, str]]:
        return None

    def entrypoint(self, node: Node) -> Optional[str]:
        return None

    def mem_limit(self, node: Node) -> Optional[str]:
        return None

    def cpus(self, node: Node) -> Optional[float]:
        return None
    
    def ports(self, node: Node) -> Optional[dict[str, str]]:
        return None

    def extra(self, topo: Topology):
        with open("data/hostfile", "w") as f:
            for node in topo.nodes.values():
                f.write(node.ip + "\n")

    def post_network_setup(self, topo: Topology, output):
        pass

    def post_pause(self, output):
        pass


class Cockroach(Application):
    def initialize(self, topo: Topology):
        self.node_names = []
        self.node_ips = []
        for node in topo.nodes.values():
            self.node_names.append(node.name)
            self.node_ips.append(node.ip)

    def image(self, node: Node) -> str:
        return 'cockroachdb/cockroach:v24.1.2'

    def volumes(self, node: Node) -> dict[str, str]:
        return {f'{node.name}': '/cockroach/cockroach-data'}

    def environment(self, node: Node) -> Optional[dict[str, str]]:
        return None

    def entrypoint(self, node: Node) -> Optional[str]:
        node_list = ','.join([ip + ":26357" for ip in self.node_ips])
        idx = self.node_ips.index(node.ip)
        return f'./cockroach start --advertise-addr={node.ip}:26357 \
                                 --http-addr={node.ip}:{8080 + idx} \
                                 --listen-addr={node.ip}:26357 \
                                 --sql-addr={node.ip}:{26257 + idx} \
                                 --insecure \
                                 --join={node_list}'

    def mem_limit(self, node: Node) -> Optional[str]:
        return "4g"

    def cpus(self, node: Node) -> Optional[float]:
        return 2
    
    def ports(self, node: Node) -> Optional[dict[str, str]]:
        idx = self.node_ips.index(node.ip)
        return {f"{26257 + idx}": f"{26257 + idx}", f"{8080 + idx}": f"{8080 + idx}"}

    def extra(self, topo: Topology):
        with print_to_script("setup-cluster.sh") as output:
            output(f'docker exec -it {self.node_names[0]} ./cockroach --host={self.node_ips[0]}:26357 init --insecure')
            output('while true; do')
            output(f'   results=$(docker exec -it {self.node_names[0]} grep \'node starting\' /cockroach/cockroach-data/logs/cockroach.log -A 11)')
            output('    if [[ -n "$results" ]]; then')
            output('        echo "$results"')
            output('        break')
            output('    fi')
            output('    sleep 1  # Wait for 1 second before trying again')
            output('done')

    def post_network_setup(self, topo: Topology, output):
        pass

    def post_pause(self, output):
        pass

    def should_create_volumes(self):
        return True
    

class Spark(Application):
    def initialize(self, topo: Topology):
        self.nodes = list(topo.nodes.values())
        self.master_name = self.nodes[0].name
        self.master_ip = self.nodes[0].ip
        pass

    def image(self, node: Node) -> str:
        return "spark:3.5.2"

    def volumes(self, node: Node) -> dict[str, str]:
        return {"./data": "/opt/spark/work-dir"}

    def environment(self, node: Node) -> Optional[dict[str, str]]:
        if node.name == self.master_name:
            return {"SPARK_MASTER_HOST": f"{node.ip}", "SPARK_LOCAL_HOSTNAME ": f"{node.ip}"}
        else:
            return {"SPARK_LOCAL_HOSTNAME ": f"{node.ip}"}

    def entrypoint(self, node: Node) -> Optional[str]:
        return "sleep inf"

    def mem_limit(self, node: Node) -> Optional[str]:
        return '8g'

    def cpus(self, node: Node) -> Optional[float]:
        return 2
    
    def ports(self, node: Node) -> Optional[dict[str, str]]:
        if node.name == self.master_name:
            return {"8080": "8080", "7077": "7077","4040": "4040"}
        else:
            for i, n in enumerate(self.nodes):
                if node.name == n.name:
                    return {f"{8081 + i}": "8081"}

    def extra(self, topo: Topology):
        with print_to_script("setup-cluster.sh") as output:
            for node in topo.nodes.values():
                if node.name == self.master_name:
                    output(f'docker exec -it {node.name} /opt/spark/sbin/start-master.sh -h {node.ip}')
                else:
                    output(f'docker exec -it {node.name} /opt/spark/sbin/start-worker.sh {self.master_ip}:7077 -h {node.ip}')

    def post_network_setup(self, topo: Topology, output):
        pass

    def post_pause(self, output):
        pass