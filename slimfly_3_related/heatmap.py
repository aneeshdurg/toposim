import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from scapy.all import rdpcap
from collections import defaultdict
import glob
import multiprocessing as mp

# ip_to_id = {
# "174.30.0.2":"h15",
# "174.34.0.2":"h17",
# "174.18.0.2":"h9",
# "174.28.0.2":"h14",
# "174.32.0.2":"h16",
# "174.36.0.2":"h18",
# "174.16.0.2":"h8",
# "174.10.0.2":"h5",
# "174.6.0.2":"h3",
# "174.4.0.2":"h2",
# "174.22.0.2":"h11",
# "174.20.0.2":"h10",
# "174.14.0.2":"h7",
# "174.12.0.2":"h6",
# "174.2.0.2":"h1",
# "174.8.0.2":"h4",
# "174.26.0.2":"h13",
# "174.24.0.2":"h12",
# }

ip_to_id = {
    "174.30.0.2":"h22",
    "174.7.0.2":"h5",
    "174.43.0.2":"h32",
    "174.68.0.2":"h51",
    "174.3.0.2":"h2",
    "174.34.0.2":"h25",
    "174.47.0.2":"h35",
    "174.38.0.2":"h28",
    "174.39.0.2":"h29",
    "174.18.0.2":"h13",
    "174.19.0.2":"h14",
    "174.58.0.2":"h43",
    "174.28.0.2":"h21",
    "174.40.0.2":"h30",
    "174.32.0.2":"h24",
    "174.42.0.2":"h31",
    "174.36.0.2":"h27",
    "174.66.0.2":"h49",
    "174.64.0.2":"h48",
    "174.71.0.2":"h53",
    "174.72.0.2":"h54",
    "174.16.0.2":"h12",
    "174.15.0.2":"h11",
    "174.10.0.2":"h7",
    "174.31.0.2":"h23",
    "174.6.0.2":"h4",
    "174.4.0.2":"h3",
    "174.44.0.2":"h33",
    "174.46.0.2":"h34",
    "174.63.0.2":"h47",
    "174.62.0.2":"h46",
    "174.60.0.2":"h45",
    "174.50.0.2":"h37",
    "174.70.0.2":"h52",
    "174.22.0.2":"h16",
    "174.54.0.2":"h40",
    "174.20.0.2":"h15",
    "174.55.0.2":"h41",
    "174.14.0.2":"h10",
    "174.12.0.2":"h9",
    "174.11.0.2":"h8",
    "174.35.0.2":"h26",
    "174.2.0.2":"h1",
    "174.48.0.2":"h36",
    "174.67.0.2":"h50",
    "174.8.0.2":"h6",
    "174.52.0.2":"h39",
    "174.27.0.2":"h20",
    "174.26.0.2":"h19",
    "174.51.0.2":"h38",
    "174.24.0.2":"h18",
    "174.56.0.2":"h42",
    "174.23.0.2":"h17",
    "174.59.0.2":"h44",
}

label = sys.argv[1]

def default_dict_int():
    return defaultdict(int)

def process_pcap_file(pcap_file):
    traffic_matrix = defaultdict(default_dict_int)
    packets = rdpcap(pcap_file)
    for pkt in packets:
        if pkt.haslayer('IP'):
            src_ip = pkt['IP'].src
            dst_ip = pkt['IP'].dst
            if src_ip in ip_to_id and dst_ip in ip_to_id:
                comp = lambda x, y: int(x[1:]) - int(y[1:])
                x = ip_to_id[src_ip]
                y = ip_to_id[dst_ip]
                if comp(x, y) < 1:
                    x, y = y, x
                traffic_matrix[x][y] += len(pkt)
    return dict(traffic_matrix)

def merge_traffic_matrices(matrices):
    merged_matrix = defaultdict(default_dict_int)
    for matrix in matrices:
        for src, dst_dict in matrix.items():
            for dst, count in dst_dict.items():
                merged_matrix[src][dst] += count
    return merged_matrix

def build_traffic_matrix(pcap_files):
    with mp.Pool(processes=4) as pool:
        results = pool.map(process_pcap_file, pcap_files)
    return merge_traffic_matrices(results)

# Function to create a heatmap from the traffic matrix
def create_heatmap(traffic_matrix):
    # Get all unique IP addresses
    names = set(traffic_matrix.keys())
    for src in traffic_matrix:
        names.update(traffic_matrix[src].keys())
    names = sorted(names, key=lambda x: int(x[1:]))

    # Create an index mapping for IP addresses
    ip_index = {ip: idx for idx, ip in enumerate(names)}

    # Initialize the traffic matrix
    matrix_size = len(names)
    matrix = np.zeros((matrix_size, matrix_size), dtype=int)

    # Populate the traffic matrix
    for src, dst_dict in traffic_matrix.items():
        for dst, count in dst_dict.items():
            matrix[ip_index[src]][ip_index[dst]] = count

    # Create the heatmap
    plt.figure(figsize=(10, 8))
    plt.imshow(matrix, cmap='hot', interpolation='nearest')
    plt.colorbar(label="Traffic Size (bytes)").set_label('Traffic Size (bytes)', rotation=270, labelpad=20)
    plt.xticks(ticks=np.arange(len(names)), labels=names, rotation=45)
    plt.yticks(ticks=np.arange(len(names)), labels=names)
    plt.xlabel('Host')
    plt.ylabel('Host')
    plt.title(f'Network Traffic Heatmap ({label})')
    output_dir = "tigergraph-heatmaps"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/host-{label}.pdf"
    plt.savefig(output_file)
    plt.close()


# Function to create a heatmap from the traffic matrix
def create_router_heatmap(traffic_matrix):
    # Get all unique IP addresses
    names = set(traffic_matrix.keys())
    for src in traffic_matrix:
        names.update(traffic_matrix[src].keys())
    names = sorted(names, key=lambda x: int(x[1:]))

    # Create an index mapping for IP addresses
    ip_index = {ip: idx for idx, ip in enumerate(names)}

    hosts_per_router = 3 # hosts per router
    num_routers = 18 # routers

    # Initialize the traffic matrix
    matrix = np.zeros((num_routers, num_routers), dtype=int)

    # Populate the traffic matrix
    for src, dst_dict in traffic_matrix.items():
        for dst, count in dst_dict.items():
            matrix[ip_index[src] // hosts_per_router][ip_index[dst] // hosts_per_router] += count

    router_names = [f'R{i}' for i in range(num_routers)]

    # Create the heatmap
    plt.figure(figsize=(10, 8))
    plt.imshow(matrix, cmap='hot', interpolation='nearest')
    plt.colorbar(label="Traffic Size (bytes)").set_label('Traffic Size (bytes)', rotation=270, labelpad=20)
    plt.xticks(ticks=np.arange(num_routers), labels=router_names, rotation=0)
    plt.yticks(ticks=np.arange(num_routers), labels=router_names)
    plt.xlabel('Router')
    plt.ylabel('Router')
    plt.title(f'Network Traffic Heatmap ({label})')
    output_dir = "tigergraph-heatmaps"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/router-{label}.pdf"
    plt.savefig(output_file)
    plt.close()


# Function to create a heatmap from the traffic matrix
def create_group_heatmap(traffic_matrix):
    # Get all unique IP addresses
    names = set(traffic_matrix.keys())
    for src in traffic_matrix:
        names.update(traffic_matrix[src].keys())
    names = sorted(names, key=lambda x: int(x[1:]))

    # Create an index mapping for IP addresses
    ip_index = {ip: idx for idx, ip in enumerate(names)}

    hosts_per_group = 9 # hosts per group
    num_groups = 6 # groups

    # Initialize the traffic matrix
    matrix = np.zeros((num_groups, num_groups), dtype=int)

    # Populate the traffic matrix
    for src, dst_dict in traffic_matrix.items():
        for dst, count in dst_dict.items():
            matrix[ip_index[src] // hosts_per_group][ip_index[dst] // hosts_per_group] += count

    group_names = [f'G{i}' for i in range(num_groups)]

    # Create the heatmap
    plt.figure(figsize=(10, 8))
    plt.imshow(matrix, cmap='hot', interpolation='nearest')
    plt.colorbar(label="Traffic Size (bytes)").set_label('Traffic Size (bytes)', rotation=270, labelpad=20)
    plt.xticks(ticks=np.arange(num_groups), labels=group_names, rotation=0)
    plt.yticks(ticks=np.arange(num_groups), labels=group_names)
    plt.xlabel('Group')
    plt.ylabel('Group')
    plt.title(f'Network Traffic Heatmap ({label})')
    output_dir = "tigergraph-heatmaps"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/group-{label}.pdf"
    plt.savefig(output_file)
    plt.close()

if __name__ == '__main__':
    # Define the path to the directory containing the pcap files
    if len(sys.argv) > 2:
        data_dir = sys.argv[2]
    else:
        data_dir = "/mnt/dhwang/tcpdump_outputs"
    pcap_files_pattern = f"{data_dir}/*_h*"
    pcap_files = glob.glob(pcap_files_pattern)

    # Build the traffic matrix and create the heatmap
    traffic_matrix = build_traffic_matrix(pcap_files)
    create_heatmap(traffic_matrix)
    create_router_heatmap(traffic_matrix)
    create_group_heatmap(traffic_matrix)
