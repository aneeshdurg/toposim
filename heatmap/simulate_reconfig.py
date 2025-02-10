#!/usr/bin/env python
"""Prediction of how much traffic is saved by dynamic reconfiguration"""

import argparse
import os
import multiprocessing as mp
import random
from dataclasses import dataclass, field

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

N = max(
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


def process_ts(ts):
    matrix = np.zeros((num_groups, num_groups))
    with open(output_dir + f"/matrix-ts{ts}.txt") as f:
        m = [[int(x.strip()) for x in l.split()] for l in f.readlines()]
        for i in range(num_groups):
            for j in range(num_groups):
                matrix[i][j] = m[i][j]

    def permute(p: int):
        # Get `p` as a bitstring showing whether each OCS state should be
        # toggled or not.
        b = bin(p)[2:]
        b = (len(tp.ocss) - len(b)) * "0" + b
        state = [c == "1" for c in b]
        # Toggle all OCS states for this permutation and get the new next-hops
        # for each path
        tp.set_ocs_states(state)
        paths = tp.paths

        combined_matrix = np.zeros((num_groups, num_groups), dtype=int)
        for src in range(6):
            for dst in range(6):
                if src == dst:
                    # print(src, dst, "+", src, dst)
                    combined_matrix[src][dst] += matrix[src][dst]
                    continue
                curr = src
                while True:
                    next_hop = paths[(curr, dst)]
                    # print(curr, next_hop, "+", src, dst)
                    combined_matrix[curr][next_hop] += matrix[src][dst]
                    curr = next_hop
                    if curr == dst:
                        break

        return combined_matrix

    ms = []
    for i in range(2 ** len(tp.ocss)):
        m = permute(i)
        ms.append(m)
    return [sum(sum(m)) for m in ms]


with mp.Pool(processes=32) as pool:
    ts_costs = pool.map(process_ts, range(N))

cost_per_config = sum(np.matrix(ts_costs))
print(f"{cost_per_config=}")
print()

print("min cost", np.min(cost_per_config))
print("min cost config", np.argmin(cost_per_config))
print("max cost", np.max(cost_per_config))
print("max cost config", np.argmax(cost_per_config))
print("mean cost", np.mean(cost_per_config))

best = np.min(cost_per_config)
worst = np.max(cost_per_config)
print("worst vs best", 100 * (worst - best) / worst, "%")


def show_report(cost, path):
    print(f"cost with reconfig every {interval}s", cost)
    if args.show_transformations:
        print("transformations:", path)
    print("min cost vs reconfig")
    print("  abs improvement: ", np.min(cost_per_config) - cost)
    print(
        "  rel improvement: ",
        100.0 * (np.min(cost_per_config) - cost) / np.min(cost_per_config),
        "%",
    )
    print("max cost vs reconfig")
    print("  abs improvement: ", np.max(cost_per_config) - cost)
    print(
        "  rel improvement: ",
        100.0 * (np.max(cost_per_config) - cost) / np.max(cost_per_config),
        "%",
    )
    print("mean cost vs reconfig")
    print("  abs improvement: ", np.mean(cost_per_config) - cost)
    print(
        "  rel improvement: ",
        100.0 * (np.mean(cost_per_config) - cost) / np.mean(cost_per_config),
        "%",
    )


print("\nOptimal Reconfiguration strategy:")
best_case = sum(min(x) for x in ts_costs)
best_path = [np.argmin(x) for x in ts_costs]
show_report(best_case, best_path)

print("\nSingle OCS change at a time reconfig strategy (oracle):")
curr_config = [int(np.argmin(ts_costs[0]))]
curr_cost = min(ts_costs[0])


def hamming_distance(a, b):
    bs_a = bin(a)[2:]
    bs_b = bin(b)[2:]
    max_len = max(len(bs_a), len(bs_b))
    bs_a = "0" * (max_len - len(bs_a)) + bs_a
    bs_b = "0" * (max_len - len(bs_b)) + bs_b
    d = 0
    for ca, cb in zip(bs_a, bs_b):
        if ca != cb:
            d += 1
    return d


for i in range(1, len(ts_costs)):
    # Evaluate every config that differs by at most 1 bit from the current config
    min_cost = -1
    min_config = -1
    for config, cost in enumerate(ts_costs[i]):
        if hamming_distance(config, curr_config[-1]) > 1:
            continue
        if min_config == -1:
            min_config = config
            min_cost = cost
        else:
            if min_cost > cost:
                min_cost = cost
                min_config = config
    assert min_config >= 0
    curr_cost += min_cost
    curr_config.append(min_config)
show_report(curr_cost, curr_config)
one_ocs_path = [k for k in curr_config]

# print("\nWorst Reconfiguration strategy:")
# worst_case = sum(max(x) for x in ts_costs)
# worst_path = [np.argmax(x) for x in ts_costs]
# show_report(worst_case, worst_path)

print("\nDelayed Reconfiguration strategy:")
curr_config = [0]
curr_cost = 0
for i in range(1, len(ts_costs)):
    curr_cost += ts_costs[i][curr_config[-1]]
    curr_config.append(np.argmin(ts_costs[i]))
show_report(curr_cost, curr_config)

print("\nRandom Reconfiguration strategy:")
random_cost = 0
random_path = []
for i in range(len(ts_costs)):
    config = random.randint(0, len(ts_costs[0]) - 1)
    random_cost += ts_costs[i][config]
    random_path.append(config)
show_report(random_cost, random_path)

print("paths", 1 - sum(np.array(best_path) == np.array(one_ocs_path)) / len(best_path))
total_diff = 0
for i in range(len(best_path)):
    if best_path[i] != one_ocs_path[i]:
        total_diff += ts_costs[i][best_path[i]] - ts_costs[i][one_ocs_path[i]]
print(total_diff)
