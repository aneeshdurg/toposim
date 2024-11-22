# TopoSim

Simulate how distributed graph databases (or any distributed application)
performs under any network topology using docker.

Usage:

```
toposim <out_dir> <config_file> [--app <janusgraph|tigergraph>]
# see --help for more options
```

See `./example.json` to see how the topology is defined. Once the topology is
generated, the application can be started with `docker compose up -d` and
networking can be enabled with `./setup-networking`. The cluster can be
paused with `./pause` and destroyed with `./cleanup`. See `tools/` in the
generated directory for additional tools to analyze traffic or the state of the
containers.

To simulate network latency or other network traffic properties, use
`add_delay/mod_delay`. Alternative, you can use establish network modification
tools like `wondershaper` in combination with `tools/run_in_ns`.

## Installing

```bash
# Install argparsh for argument parsing in generated scripts
# option 1:
# install rust
# $ curl https://sh.rustup.rs -sSf | sh -s -- -y
# $ . ~/.cargo/env
# $ cargo install argparsh
# option2 :
# $ pip install argparsh

# Install geni-lib for cloudlab deployment (optional)
git clone https://gitlab.flux.utah.edu/emulab/geni-lib
cd geni-lib
pip install .
cd ..

git clone https://github.com/aneeshdurg/toposim
cd toposim
pip install .
```

## Supported Applications

+ [JanusGraph](https://janusgraph.org)
+ [TigerGraph](https://www.tigergraph.com/)
    - Note that TigerGraph requires a license.
+ [Galois](https://github.com/IntelligentSoftwareSystems/Galois)
    - Note that running Galois requires building the docker image first. See
      [here](./toposim/appdata/galois/README.md)
