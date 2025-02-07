#!/usr/bin/env python
"""Prediction of how much traffic is saved by dynamic reconfiguration"""

import argparse
import os
import multiprocessing as mp
import random

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

def compute_cost(matrix, paths):
    combined_matrix = np.zeros((num_groups, num_groups), dtype=int)
    for src in range(num_groups):
        for dst in range(num_groups):
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
    return sum(sum(combined_matrix))

def intergroup_process_ts(ts):
    matrix = np.zeros((num_groups, num_groups))
    with open(output_dir + f"/matrix-ts{ts}.txt") as f:
        m = [[int(x.strip()) for x in l.split()] for l in f.readlines()]
        for i in range(num_groups):
            for j in range(num_groups):
                matrix[i][j] = m[i][j]
                
    cost_no_reconfig = compute_cost(matrix, paths_)
    # Step 1. Split the matrix into sub-matrices for each OCS
    def split_matrix(matrix):
        sub_matrices = []
        NR = len(racks)
        for i in range(NR):
            for j in range(i + 1, NR):
                rack1 = racks[i]
                rack2 = racks[j]
                sub_matrix = np.zeros((2, 2))
                for g1 in range(2):
                    for g2 in range(2):
                        # print(f'{g1} {g2} {rack1[g1]} {rack2[g2]} {matrix[rack1[g1]][rack2[g2]]} {matrix[rack2[g2]][rack1[g1]]}')
                        sub_matrix[g1][g2] += matrix[rack1[g1]][rack2[g2]]
                        sub_matrix[g1][g2] += matrix[rack2[g2]][rack1[g1]]
                sub_matrices.append(sub_matrix)
        return sub_matrices
            
    # print(matrix)
    sub_matrices = split_matrix(matrix)
    CROSS = 0
    BAR = 1
    def ocs_state(matrix):
        return BAR if matrix[0][0] + matrix[1][1] > matrix[0][1] + matrix[1][0] else CROSS
    # Step 2. Compute the OCS state of each sub-matrix
    ocs_states = []
    for sub_matrix in sub_matrices:
        ocs_states.append(ocs_state(sub_matrix))
        # print(sub_matrix)
        # if ocs_states[-1] == BAR:
        #     print("BAR")
        # else:
        #     print("CROSS")
    # Step 3. Reconfigure the cross-connection of OCSes
    def reconfigure(ocs_states):
        paths = {k: v for k, v in paths_.items()}
        NR = len(racks)
        ocs_id = 0
        for i in range(NR):
            for j in range(i + 1, NR):
                if ocs_states[ocs_id] == BAR:
                    rack1 = racks[i]
                    rack2 = racks[j]
                    for k in range(2):
                        group1 = rack1[k]
                        group2 = rack2[k]
                        # print(f'path {group1} {group2} {paths[(group1, group2)]} -> ', end='')
                        paths[(group1, group2)] = group2
                        paths[(group2, group1)] = group1
                        # print(f'path {group1} {group2} {paths[(group1, group2)]}')
                ocs_id += 1 # use the equation if q >= 5
        return paths
    paths = reconfigure(ocs_states)
    cost = compute_cost(matrix, paths)
    # print(cost)
    return cost, cost_no_reconfig

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
            
        print(paths)

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
    bs_a = '0' * (max_len - len(bs_a)) + bs_a
    bs_b = '0' * (max_len - len(bs_b)) + bs_b
    d = 0
    for (ca, cb) in zip(bs_a, bs_b):
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

# print("\nRandom Reconfiguration strategy:")
# random_cost = 0
# random_path = []
# for i in range(len(ts_costs)):
#     config = random.randint(0, len(ts_costs[0]) - 1)
#     random_cost += ts_costs[i][config]
#     random_path.append(config)
# show_report(random_cost, random_path)


print("\nIntergroup Reconfiguration strategy:")
# intergroup_proccess_ts returns a array of two elements, the first element is the cost with reconfig, the second element is the cost without reconfig at each timestamp
with mp.Pool(processes=32) as pool:
    ts_costs = pool.map(intergroup_process_ts, range(N))

total_cost = sum([x[0] for x in ts_costs])
print(f"cost with reconfig every {interval}s", total_cost)
total_cost_no_reconfig = sum([x[1] for x in ts_costs])
print(f"cost without reconfig", total_cost_no_reconfig)
print("cost without reconfig vs reconfig")
print("  abs improvement:", total_cost_no_reconfig - total_cost)
print("  rel improvement:", 100 * (total_cost_no_reconfig - total_cost) / total_cost_no_reconfig)