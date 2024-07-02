import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from scapy.all import rdpcap
from collections import defaultdict
import yaml
import re

mac_to_names = {
    "02:42:ae:13:00:03":"r10",
    "02:42:ae:16:00:02":"h11",
    "02:42:ae:63:00:02":"r9",
    "02:42:ae:63:00:03":"r12",
    "02:42:ae:16:00:03":"port21",
    "02:42:ae:2e:00:02":"r10",
    "02:42:ae:28:00:03":"r13",
    "02:42:ae:2e:00:03":"r12",
    "02:42:ae:28:00:02":"r8",
    "02:42:ae:5f:00:02":"r7",
    "02:42:ae:5f:00:03":"r10",
    "02:42:ae:09:00:03":"r5",
    "02:42:ae:29:00:02":"r3",
    "02:42:ae:29:00:03":"port5",
    "02:42:ae:52:00:02":"r17",
    "02:42:ae:57:00:03":"r11",
    "02:42:ae:52:00:03":"port33",
    "02:42:ae:57:00:02":"r5",
    "02:42:ae:07:00:03":"r4",
    "02:42:ae:47:00:02":"r7",
    "02:42:ae:47:00:03":"port13",
    "02:42:ae:3e:00:03":"r3",
    "02:42:ae:3e:00:02":"r1",
    "02:42:ae:37:00:03":"port11",
    "02:42:ae:43:00:02":"r4",
    "02:42:ae:43:00:03":"r6",
    "02:42:ae:37:00:02":"r6",
    "02:42:ae:31:00:03":"port7",
    "02:42:ae:4e:00:02":"r1",
    "02:42:ae:31:00:02":"r4",
    "02:42:ae:4e:00:03":"r13",
    "02:42:ae:36:00:02":"r10",
    "02:42:ae:1e:00:03":"port29",
    "02:42:ae:1e:00:02":"h15",
    "02:42:ae:36:00:03":"r11",
    "02:42:ae:22:00:03":"port33",
    "02:42:ae:27:00:02":"r7",
    "02:42:ae:22:00:02":"h17",
    "02:42:ae:27:00:03":"r8",
    "02:42:ae:14:00:02":"h10",
    "02:42:ae:61:00:02":"r13",
    "02:42:ae:14:00:03":"port19",
    "02:42:ae:61:00:03":"r14",
    "02:42:ae:2f:00:03":"r3",
    "02:42:ae:1b:00:03":"r14",
    "02:42:ae:2f:00:02":"r2",
    "02:42:ae:5a:00:03":"port29",
    "02:42:ae:54:00:02":"r13",
    "02:42:ae:5a:00:02":"r15",
    "02:42:ae:54:00:03":"port25",
    "02:42:ae:02:00:03":"port1",
    "02:42:ae:50:00:02":"r5",
    "02:42:ae:02:00:02":"h1",
    "02:42:ae:50:00:03":"r6",
    "02:42:ae:04:00:03":"port3",
    "02:42:ae:04:00:02":"h2",
    "02:42:ae:59:00:03":"port19",
    "02:42:ae:0f:00:03":"r8",
    "02:42:ae:59:00:02":"r10",
    "02:42:ae:03:00:03":"r2",
    "02:42:ae:38:00:02":"r11",
    "02:42:ae:38:00:03":"r12",
    "02:42:ae:46:00:03":"port27",
    "02:42:ae:3b:00:02":"r6",
    "02:42:ae:3b:00:03":"r12",
    "02:42:ae:46:00:02":"r14",
    "02:42:ae:0a:00:02":"h5",
    "02:42:ae:40:00:03":"port35",
    "02:42:ae:0a:00:03":"port9",
    "02:42:ae:40:00:02":"r18",
    "02:42:ae:4b:00:03":"r15",
    "02:42:ae:21:00:03":"r17",
    "02:42:ae:4b:00:02":"r5",
    "02:42:ae:1c:00:03":"port27",
    "02:42:ae:49:00:02":"r3",
    "02:42:ae:1f:00:03":"r16",
    "02:42:ae:1c:00:02":"h14",
    "02:42:ae:49:00:03":"r18",
    "02:42:ae:25:00:02":"r4",
    "02:42:ae:11:00:03":"r9",
    "02:42:ae:25:00:03":"r10",
    "02:42:ae:17:00:03":"r12",
    "02:42:ae:62:00:03":"r17",
    "02:42:ae:2c:00:02":"r6",
    "02:42:ae:62:00:02":"r16",
    "02:42:ae:2c:00:03":"r17",
    "02:42:ae:10:00:02":"h8",
    "02:42:ae:10:00:03":"port15",
    "02:42:ae:08:00:03":"port7",
    "02:42:ae:5b:00:02":"r8",
    "02:42:ae:08:00:02":"h4",
    "02:42:ae:5b:00:03":"r18",
    "02:42:ae:55:00:03":"r2",
    "02:42:ae:55:00:02":"r1",
    "02:42:ae:53:00:03":"r15",
    "02:42:ae:53:00:02":"r14",
    "02:42:ae:0e:00:02":"h7",
    "02:42:ae:0e:00:03":"port13",
    "02:42:ae:3a:00:03":"r10",
    "02:42:ae:45:00:02":"r17",
    "02:42:ae:45:00:03":"r18",
    "02:42:ae:3a:00:02":"r1",
    "02:42:ae:33:00:03":"r16",
    "02:42:ae:3f:00:02":"r7",
    "02:42:ae:33:00:02":"r5",
    "02:42:ae:3f:00:03":"r9",
    "02:42:ae:4d:00:03":"port21",
    "02:42:ae:4a:00:02":"r2",
    "02:42:ae:4d:00:02":"r11",
    "02:42:ae:4a:00:03":"r11",
    "02:42:ae:20:00:03":"port31",
    "02:42:ae:1d:00:03":"r15",
    "02:42:ae:20:00:02":"h16",
    "02:42:ae:26:00:03":"port9",
    "02:42:ae:34:00:02":"r7",
    "02:42:ae:34:00:03":"r15",
    "02:42:ae:26:00:02":"r5",
    "02:42:ae:5d:00:02":"r4",
    "02:42:ae:2d:00:03":"r17",
    "02:42:ae:5d:00:03":"r5",
    "02:42:ae:2d:00:02":"r7",
    "02:42:ae:56:00:02":"r2",
    "02:42:ae:56:00:03":"r14",
    "02:42:ae:06:00:03":"port5",
    "02:42:ae:06:00:02":"h3",
    "02:42:ae:58:00:02":"r16",
    "02:42:ae:58:00:03":"r18",
    "02:42:ae:39:00:03":"r16",
    "02:42:ae:01:00:03":"r1",
    "02:42:ae:39:00:02":"r1",
    "02:42:ae:42:00:03":"port23",
    "02:42:ae:18:00:02":"h12",
    "02:42:ae:18:00:03":"port23",
    "02:42:ae:42:00:02":"r12",
    "02:42:ae:35:00:03":"r11",
    "02:42:ae:30:00:02":"r6",
    "02:42:ae:35:00:02":"r8",
    "02:42:ae:30:00:03":"r13",
    "02:42:ae:1a:00:03":"port25",
    "02:42:ae:4c:00:02":"r9",
    "02:42:ae:1a:00:02":"h13",
    "02:42:ae:4c:00:03":"r16",
    "02:42:ae:48:00:03":"port31",
    "02:42:ae:48:00:02":"r16",
    "02:42:ae:23:00:03":"r18",
    "02:42:ae:60:00:03":"r12",
    "02:42:ae:15:00:03":"r11",
    "02:42:ae:60:00:02":"r3",
    "02:42:ae:2b:00:03":"r14",
    "02:42:ae:2b:00:02":"r9",
    "02:42:ae:5e:00:03":"r15",
    "02:42:ae:5e:00:02":"r3",
    "02:42:ae:5c:00:03":"port15",
    "02:42:ae:12:00:02":"h9",
    "02:42:ae:12:00:03":"port17",
    "02:42:ae:5c:00:02":"r8",
    "02:42:ae:51:00:03":"r15",
    "02:42:ae:51:00:02":"r13",
    "02:42:ae:05:00:03":"r3",
    "02:42:ae:0b:00:03":"r6",
    "02:42:ae:0d:00:03":"r7",
    "02:42:ae:0c:00:02":"h6",
    "02:42:ae:3c:00:03":"port17",
    "02:42:ae:0c:00:03":"port11",
    "02:42:ae:3c:00:02":"r9",
    "02:42:ae:44:00:03":"port1",
    "02:42:ae:41:00:02":"r2",
    "02:42:ae:41:00:03":"port3",
    "02:42:ae:44:00:02":"r1",
    "02:42:ae:4f:00:03":"r14",
    "02:42:ae:32:00:02":"r8",
    "02:42:ae:19:00:03":"r13",
    "02:42:ae:4f:00:02":"r4",
    "02:42:ae:32:00:03":"r9",
    "02:42:ae:3d:00:02":"r2",
    "02:42:ae:3d:00:03":"r17",
    "02:42:ae:24:00:03":"port35",
    "02:42:ae:2a:00:02":"r4",
    "02:42:ae:24:00:02":"h18",
    "02:42:ae:2a:00:03":"r18",
}

query = sys.argv[1]

# Function to parse pcap files and build the traffic matrix
def build_traffic_matrix(pcap_files):
    traffic_matrix = defaultdict(lambda: defaultdict(int))
    for pcap_file in pcap_files:
        packets = rdpcap(pcap_file)
        for pkt in packets:
            if pkt.haslayer('Ether'):
                src_mac = pkt['Ether'].src
                dst_mac = pkt['Ether'].dst
                if src_mac in mac_to_names.keys() and dst_mac in mac_to_names.keys():
                    traffic_matrix[mac_to_names[src_mac]][mac_to_names[dst_mac]] += len(pkt)
    return traffic_matrix

# Function to create a heatmap from the traffic matrix
def create_heatmap(traffic_matrix):
    # Get all unique MAC addresses
    names = set(traffic_matrix.keys())
    for src in traffic_matrix:
        names.update(traffic_matrix[src].keys())
    names = sorted(names, key=lambda x: int(x[1:]))
    
    # Create an index mapping for MAC addresses
    mac_index = {mac: idx for idx, mac in enumerate(names)}
    
    # Initialize the traffic matrix
    matrix_size = len(names)
    matrix = np.zeros((matrix_size, matrix_size), dtype=int)
    
    # Populate the traffic matrix
    for src, dst_dict in traffic_matrix.items():
        for dst, count in dst_dict.items():
            matrix[mac_index[src]][mac_index[dst]] = count
    
    # Create the heatmap
    plt.figure(figsize=(10, 8))
    plt.imshow(matrix, cmap='hot', interpolation='nearest')
    plt.colorbar(label="Traffic Size (bytes)").set_label('Traffic Size (bytes)', rotation=270, labelpad=20)
    plt.xticks(ticks=np.arange(len(names)), labels=names)
    plt.yticks(ticks=np.arange(len(names)), labels=names)
    plt.xlabel('Destination')
    plt.ylabel('Source')
    plt.title(f'Network Traffic Heatmap (Q{query})')
    output_dir = "tigergraph-heatmaps"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/link-q{query}.pdf"
    plt.savefig(output_file)
    plt.close()

# Define the path to the directory containing the pcap files
links_file = 'slimfly_3/links.yml'
with open(links_file, 'r') as f:
    all_links = yaml.safe_load(f)

pcap_files = []
for src, dst_ifaces in all_links.items():
    if re.match('slimfly_3_r', src):
        for dst, iface in dst_ifaces.items():
            if re.match('slimfly_3_r', dst):
                pcap_files.append(f'/mnt/dhwang/tcpdump_outputs/dumpfile_{src}_{iface}.pcap')
                
# Build the traffic matrix and create the heatmap
traffic_matrix = build_traffic_matrix(pcap_files)
create_heatmap(traffic_matrix)
