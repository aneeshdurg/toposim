import argparse
import os
import multiprocessing as mp
from dataclasses import dataclass, field
from typing import Callable, cast

from numba import cuda
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument(
    "output_dir", help="Location of matrix-ts*.txt files (from heatmap)"
)
parser.add_argument("interval", type=float, help="Interval between each matrix")
parser.add_argument("--num-groups", type=int, default=6)
parser.add_argument("--show-transformations", action="store_true")
args = parser.parse_args()

num_groups = args.num_groups
output_dir = args.output_dir
interval = args.interval

num_files = 1 + max(
    [
        int(f.split(".")[0].split("-")[1][2:])
        for f in os.listdir(output_dir)
        if f.endswith(".txt")
    ]
)


@dataclass
class Node:
    id_: int

    def __hash__(self):
        return hash(self.id_)


@dataclass
class Rack:
    "Two nodes in the same rack (immutable)"
    nodes: tuple[Node, Node]


@dataclass
class OCS:
    rack: tuple[Rack, Rack]
    # If state is false:
    #   rack[0][0] -> rack[1][1]/rack[0][1] -> rack[0][0]
    # Else:
    #   rack[0][0] -> rack[1][0]/rack[0][1] -> rack[0][1]
    state: bool = False

    def adjacent(self, n: Node) -> Node:
        "Determine what node `n` is connected to via the OCS link"
        if n in self.rack[0].nodes:
            i = self.rack[0].nodes.index(n)
            if self.state:
                return self.rack[1].nodes[i]
            return self.rack[1].nodes[(i + 1) % 2]

        assert n in self.rack[1].nodes
        i = self.rack[1].nodes.index(n)
        if self.state:
            return self.rack[0].nodes[i]
        return self.rack[0].nodes[(i + 1) % 2]


@dataclass
class Topology:
    ocss: list[OCS]
    adjacency: dict[Node, set[Node]] = field(default_factory=lambda: {})
    paths: dict[tuple[int, int], int] = field(default_factory=lambda: {})

    def __post_init__(self):
        self.rebuild_all()

    def rebuild_all(self):
        self.rebuild_adjacency()
        self.rebuild_paths()

    def rebuild_adjacency(self):
        adj = {}
        for ocs in self.ocss:
            ocs_nodes = []
            for r in ocs.rack:
                if r.nodes[0] not in adj:
                    adj[r.nodes[0]] = set()
                if r.nodes[1] not in adj:
                    adj[r.nodes[1]] = set()

                adj[r.nodes[0]].add(r.nodes[1])
                adj[r.nodes[1]].add(r.nodes[0])
                ocs_nodes.append(r.nodes[0])
                ocs_nodes.append(r.nodes[1])
            for n in ocs_nodes:
                adj[n].add(ocs.adjacent(n))

        self.adjacency = adj

    def rebuild_paths(self):
        paths: dict[tuple[Node, Node], tuple[list[Node], float]] = {}

        # Floyd-Warshall all shortest paths
        for src in self.adjacency:
            for dst in self.adjacency:
                if src == dst:
                    continue
                dist = float("inf")
                if dst in self.adjacency[src]:
                    dist = 1
                paths[(src, dst)] = ([dst], dist)

        for n in self.adjacency:
            for src in self.adjacency:
                for dst in self.adjacency:
                    if src.id_ == dst.id_:
                        continue

                    if n == src or n == dst:
                        continue
                    curr_cost = paths[(src, dst)][1]
                    new_cost = paths[(src, n)][1] + paths[(n, dst)][1]
                    if new_cost < curr_cost:
                        paths[(src, dst)] = (
                            paths[(src, n)][0] + paths[(n, dst)][0],
                            new_cost,
                        )
        # Convert Node to int for compatibility with existing code
        self.paths = {}
        for k in paths:
            self.paths[(k[0].id_, k[1].id_)] = paths[k][0][0].id_

    def set_ocs_states(self, states: list[bool]):
        assert len(states) == len(self.ocss)
        for s, ocs in zip(states, self.ocss):
            ocs.state = s
        self.rebuild_all()


# Model slimfly as Node/Rack/OCSs
n0 = Node(0)
n1 = Node(1)
n2 = Node(2)
n3 = Node(3)
n4 = Node(4)
n5 = Node(5)

r0 = Rack((n0, n3))
r1 = Rack((n1, n4))
r2 = Rack((n2, n5))

ocs = [OCS((r0, r1)), OCS((r0, r2)), OCS((r1, r2))]
tp = Topology(ocs)

adjacencies = []
for p in range(2 ** len(tp.ocss)):
    # Get `p` as a bitstring showing whether each OCS state should be
    # toggled or not.
    b = bin(p)[2:]
    b = (len(tp.ocss) - len(b)) * "0" + b
    state = [c == "1" for c in b]
    # Toggle all OCS states for this permutation and get the new next-hops
    # for each path
    tp.set_ocs_states(state)
    paths = tp.paths

    matrix = np.zeros((num_groups, num_groups), dtype=np.uint64)
    for i in range(num_groups):
        for j in range(num_groups):
            if i == j:
                matrix[i, j] = i
            else:
                matrix[i, j] = paths[(i, j)]
    adjacencies.append(matrix)
adjacencies = np.array(adjacencies)


def factorial(x: int) -> int:
    if x <= 1:
        return 1
    total = 1
    for i in range(2, x + 1):
        total *= i
    return total


cu_factorial = cast(Callable[[int], int], cuda.jit(factorial))


@cuda.jit
def get_permutation(n: int, output):
    numbers = cuda.local.array(6, dtype=np.uint32)
    numbers[0] = 1
    numbers[1] = 2
    numbers[2] = 3
    numbers[3] = 4
    numbers[4] = 5
    numbers[5] = 6

    curr = n
    for i in range(5, -1, -1):
        v = cu_factorial(i)
        skip = curr // v
        d = 0
        pick = 0
        while True:
            if numbers[pick]:
                if skip == 0:
                    d = numbers[pick]
                    numbers[pick] = 0
                    break
                skip -= 1
            pick = (pick + 1) % 6
        output[6 - (i + 1)] = d
        curr %= v

    for i in range(6):
        output[i] -= 1


@cuda.jit
def test(output, adjacencies, traffic_per_ts):
    idx: int = cuda.blockIdx.x
    ts: int = cuda.blockIdx.y
    tp: int = cuda.blockIdx.z

    numbers = cuda.local.array(6, dtype=np.uint32)
    for i in range(6):
        numbers[i] = i + 1

    perm = cuda.local.array(6, dtype=np.uint32)
    get_permutation(idx, perm)

    total_bytes = 0
    for src in range(6):
        for dst in range(6):
            if src == dst:
                total_bytes += traffic_per_ts[ts][perm[src], perm[src]]
                continue
            curr = src
            while curr != dst:
                next_hop = adjacencies[tp][int(curr), dst]
                total_bytes += traffic_per_ts[ts][perm[int(curr)], perm[dst]]
                curr = next_hop

    output[ts][idx][tp] = total_bytes


def file_to_matrix(ts: int):
    with open(output_dir + f"/matrix-ts{ts}.txt") as f:
        matrix = np.zeros((num_groups, num_groups))
        m = [[int(x.strip()) for x in l.split()] for l in f.readlines()]
        for i in range(num_groups):
            for j in range(num_groups):
                matrix[i][j] = m[i][j]
    return matrix


with mp.Pool(processes=32) as pool:
    traffic_per_ts = pool.map(file_to_matrix, range(num_files))
traffic_per_ts = np.array(traffic_per_ts)

d_traffic_per_ts = cuda.to_device(traffic_per_ts)
d_adjacencies = cuda.to_device(adjacencies)
output = np.zeros((
    num_files,
    factorial(6),
    2 ** len(tp.ocss),
), dtype=np.uint64)

d_output = cuda.to_device(output)
b_dim = (factorial(6), num_files, 2 ** len(tp.ocss))
test[b_dim, (1, 1)](d_output, d_adjacencies, d_traffic_per_ts)
output = d_output.copy_to_host()

# output[timestamp][relabeling][OCS state]
print(sum(output[:, 0, 0]), end='|')
print(sum(np.min(ts) for ts in output[:, 0, :]))
