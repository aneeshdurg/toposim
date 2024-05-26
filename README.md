# TopoSim

Simulate how distributed graph databases (or any distributed application)
performs under any network topology using docker.

Usage:

```
python -m toposim <out_dir> <config_file> [--app <janusgraph|tigergraph>]
```

See `./example.json` to see how the topology is defined. Once the topology is
generated, the application can be started with `docker compose up -d` and
networking can be enabled with `./setup-networking.sh`. The cluster can be
paused with `./pause.sh` and destroyed with `./cleanup.sh`.

To simulate network latency or other network traffic properties, modify the
commands in `add-delay.sh`.
