#!/usr/bin/env python
"""Prediction of how much traffic is saved by dynamic reconfiguration"""

import argparse
import sys
import os
import multiprocessing as mp

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

paths_ = {
    (0, 1): 4,
    (0, 2): 5,
    (0, 3): 3,
    (0, 4): 4,
    (0, 5): 5,
    (1, 0): 3,
    (1, 2): 5,
    (1, 3): 3,
    (1, 4): 4,
    (1, 5): 5,
    (2, 0): 3,
    (2, 1): 5,
    (2, 3): 3,
    (2, 4): 4,
    (2, 5): 5,
    (3, 0): 0,
    (3, 1): 1,
    (3, 2): 2,
    (3, 4): 1,
    (3, 5): 2,
    (4, 0): 0,
    (4, 1): 1,
    (4, 2): 2,
    (4, 3): 0,
    (4, 5): 2,
    (5, 0): 0,
    (5, 1): 1,
    (5, 2): 2,
    (5, 3): 1,
    (5, 4): 1,
}
racks = [[0, 3], [1, 4], [2, 5]]


def process_ts(ts):
    matrix = np.zeros((num_groups, num_groups))
    with open(output_dir + f"/matrix-ts{ts}.txt") as f:
        m = [[int(x.strip()) for x in l.split()] for l in f.readlines()]
        for i in range(num_groups):
            for j in range(num_groups):
                matrix[i][j] = m[i][j]

    def permute(p: int):
        paths = {k: v for k, v in paths_.items()}
        b = bin(p)[2:]
        b = (len(racks) - len(b)) * "0" + b
        for i in range(len(racks)):
            if b[i] == "0":
                continue

            def swap(x):
                if x == racks[i][0]:
                    x = racks[i][1]
                elif x == racks[i][1]:
                    x = racks[i][0]
                return x

            new_paths = {}
            # swap racks[i][0] and racks[i][1]
            for k, v in paths.items():
                start = swap(k[0])
                end = swap(k[1])
                v = swap(v)
                new_paths[(start, end)] = v
            paths = new_paths

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
    for i in range(2 ** len(racks)):
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
print("worst vs best", (worst - best) / worst)

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

print("\nWorst Reconfiguration strategy:")
worst_case = sum(max(x) for x in ts_costs)
worst_path = [np.argmax(x) for x in ts_costs]
show_report(worst_case, worst_path)
