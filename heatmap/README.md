# Heatmap generation utility

Utility to generate heatmaps from toposim pcaps.

## Building

```bash
cargo install --path .
```

## Usage

```bash
# in the generated toposim directory, supposed we have pcaps collected with
# tools/tcpdump in the directory my_experiement_pcap. e.g. :
# .
# ├── add_delay
# ├── cleanup
# ├── docker-compose.yml
# ├── links.yml
# ├── mod_delay
# ├── pause
# ├── resume
# ├── setup-cluster.sh
# ├── setup_networking
# ├── tools
# │   ├── collect_queue_depth
# │   ├── egress
# │   ├── get_mac
# │   ├── limit_bandwidth
# │   ├── run_in_ns
# │   └── tcpdump
# ├── topology.json
# └── my_experiment_pcap
#     └── ....<PCAP FILES>....
# Run the following

heatmap my_experiment_pcap/ out --interval <interval in sec, default=10>

# The above will create a directory `out` which will have heatmaps generated for 
# each interval.
```

See `heatmap --help` for more info.
`--nprocs` can be used to configure the number of threads (default 16).
