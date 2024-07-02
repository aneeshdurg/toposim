import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from scapy.all import rdpcap
from collections import defaultdict
import glob

ip_to_id = {
"174.30.0.2":"h15",
"174.85.0.2":"r1",
"174.7.0.3":"r4",
"174.85.0.3":"r2",
"174.43.0.2":"r9",
"174.43.0.3":"r14",
"174.68.0.2":"r1",
"174.34.0.2":"h17",
"174.81.0.2":"r13",
"174.81.0.3":"r15",
"174.3.0.3":"r2",
"174.47.0.2":"r2",
"174.47.0.3":"r3",
"174.38.0.2":"r5",
"174.39.0.3":"r8",
"174.39.0.2":"r7",
"174.65.0.2":"r2",
"174.96.0.2":"r3",
"174.97.0.3":"r14",
"174.96.0.3":"r12",
"174.97.0.2":"r13",
"174.95.0.3":"r10",
"174.95.0.2":"r7",
"174.92.0.2":"r8",
"174.19.0.3":"r10",
"174.18.0.2":"h9",
"174.58.0.2":"r1",
"174.58.0.3":"r10",
"174.98.0.2":"r16",
"174.28.0.2":"h14",
"174.98.0.3":"r17",
"174.40.0.3":"r13",
"174.40.0.2":"r8",
"174.32.0.2":"h16",
"174.42.0.3":"r18",
"174.87.0.2":"r5",
"174.5.0.3":"r3",
"174.42.0.2":"r4",
"174.87.0.3":"r11",
"174.36.0.2":"h18",
"174.83.0.2":"r14",
"174.83.0.3":"r15",
"174.1.0.3":"r1",
"174.61.0.2":"r2",
"174.61.0.3":"r17",
"174.89.0.2":"r10",
"174.66.0.2":"r12",
"174.64.0.2":"r18",
"174.76.0.2":"r9",
"174.76.0.3":"r16",
"174.71.0.2":"r7",
"174.72.0.2":"r16",
"174.73.0.3":"r18",
"174.73.0.2":"r3",
"174.16.0.2":"h8",
"174.17.0.3":"r9",
"174.15.0.3":"r8",
"174.10.0.2":"h5",
"174.99.0.3":"r12",
"174.99.0.2":"r9",
"174.31.0.3":"r16",
"174.6.0.2":"h3",
"174.84.0.2":"r13",
"174.86.0.3":"r14",
"174.33.0.3":"r17",
"174.4.0.2":"h2",
"174.86.0.2":"r2",
"174.44.0.3":"r17",
"174.44.0.2":"r6",
"174.46.0.3":"r12",
"174.46.0.2":"r10",
"174.62.0.3":"r3",
"174.63.0.2":"r7",
"174.62.0.2":"r1",
"174.63.0.3":"r9",
"174.60.0.2":"r9",
"174.9.0.3":"r5",
"174.75.0.3":"r15",
"174.74.0.2":"r2",
"174.75.0.2":"r5",
"174.74.0.3":"r11",
"174.50.0.2":"r8",
"174.77.0.2":"r11",
"174.50.0.3":"r9",
"174.25.0.3":"r13",
"174.57.0.3":"r16",
"174.70.0.2":"r14",
"174.22.0.2":"h11",
"174.57.0.2":"r1",
"174.54.0.2":"r10",
"174.20.0.2":"h10",
"174.21.0.3":"r11",
"174.54.0.3":"r11",
"174.55.0.2":"r6",
"174.14.0.2":"h7",
"174.12.0.2":"h6",
"174.13.0.3":"r7",
"174.11.0.3":"r6",
"174.41.0.2":"r3",
"174.69.0.2":"r17",
"174.69.0.3":"r18",
"174.35.0.3":"r18",
"174.80.0.3":"r6",
"174.45.0.2":"r7",
"174.2.0.2":"h1",
"174.45.0.3":"r17",
"174.80.0.2":"r5",
"174.37.0.3":"r10",
"174.37.0.2":"r4",
"174.82.0.2":"r17",
"174.49.0.2":"r4",
"174.48.0.3":"r13",
"174.48.0.2":"r6",
"174.88.0.3":"r18",
"174.67.0.2":"r4",
"174.88.0.2":"r16",
"174.67.0.3":"r6",
"174.8.0.2":"h4",
"174.53.0.3":"r11",
"174.52.0.2":"r7",
"174.26.0.2":"h13",
"174.52.0.3":"r15",
"174.27.0.3":"r14",
"174.53.0.2":"r8",
"174.51.0.3":"r16",
"174.94.0.2":"r3",
"174.94.0.3":"r15",
"174.24.0.2":"h12",
"174.51.0.2":"r5",
"174.93.0.3":"r5",
"174.56.0.2":"r11",
"174.56.0.3":"r12",
"174.23.0.3":"r12",
"174.93.0.2":"r4",
"174.90.0.2":"r15",
"174.91.0.3":"r18",
"174.91.0.2":"r8",
"174.59.0.3":"r12",
"174.59.0.2":"r6",
"174.79.0.3":"r14",
"174.78.0.2":"r1",
"174.79.0.2":"r4",
"174.78.0.3":"r13",
"174.29.0.3":"r15",

}

query = sys.argv[1]

# Function to parse pcap files and build the traffic matrix
def build_traffic_matrix(pcap_files):
    traffic_matrix = defaultdict(lambda: defaultdict(int))
    for pcap_file in pcap_files:
        packets = rdpcap(pcap_file)
        for pkt in packets:
            if pkt.haslayer('IP'):
                src_ip = pkt['IP'].src
                dst_ip = pkt['IP'].dst
                # traffic_matrix[src_ip][dst_ip] += len(pkt)
                if src_ip in ip_to_id.keys() and dst_ip in ip_to_id.keys():
                    traffic_matrix[ip_to_id[src_ip]][ip_to_id[dst_ip]] += len(pkt)
    return traffic_matrix

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
    plt.xticks(ticks=np.arange(len(names)), labels=names, rotation=0)
    plt.yticks(ticks=np.arange(len(names)), labels=names)
    plt.xlabel('Destination')
    plt.ylabel('Source')
    plt.title(f'Network Traffic Heatmap (Q{query})')
    output_dir = "tigergraph-heatmaps"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/host-q{query}.pdf"
    plt.savefig(output_file)
    plt.close()

# Define the path to the directory containing the pcap files
pcap_files_pattern = "/mnt/dhwang/tcpdump_outputs/dumpfile_slimfly_3_h*"

# Build the traffic matrix and create the heatmap
traffic_matrix = build_traffic_matrix(glob.glob(pcap_files_pattern))
create_heatmap(traffic_matrix)
