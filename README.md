# TopoSim

Simulate how distributed graph databases (or any distributed application)
performs under any network topology using docker.

Usage:

```
toposim <out_dir> <config_file> [--app <janusgraph|tigergraph>]
# see --help for more options
# Note that --app is not required if `config_file` has a "app" key/value.
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

## Deploying on cloudlab (WIP)

If you don't have write access to this repo, you will need to first clone this
repository then set the environment variable `TOPOSIM_URL` as follows:
```bash
export TOPOSIM_URL="https://github.com/<your username>/toposim/archive/refs/heads/<branch name>.tar.gz"

# e.g. if you cloned aneeshdurg/toposim to foobar/toposim, and are using the default branch "main"
# export TOPOSIM_URL="https://github.com/foobar/toposim/archive/refs/heads/main.tar.gz"

# e.g. if you cloned aneeshdurg/toposim to myuser/toposim, and are using the default branch "branch1"
# export TOPOSIM_URL="https://github.com/myuser/toposim/archive/refs/heads/branch1.tar.gz"
```

Modify `cloudlab/config.json` to hold the topology you want. Instantiate the
config, for example:

```bash
toposim galois-experiment cloudlab/config.json --app galois
```

Create an [rspec](https://docs.cloudlab.us/advanced-topics.html#(part._rspecs))
by running `python galois-experiment/to_geni.py > profile.rspec`. Upload the
profile to cloudlab and instantiate it!

Note: This is experimental/WIP. Currently the cloudlab profile will create
nodes, setup the appropriate network routes, and install docker, but doesn't
actually start the workload.

## Supported Applications

+ [JanusGraph](https://janusgraph.org)
+ [TigerGraph](https://www.tigergraph.com/)
    - Note that TigerGraph requires a license.
+ [Galois](https://github.com/IntelligentSoftwareSystems/Galois)
    - Note that running Galois requires building the docker image first. See
      [here](./toposim/appdata/galois/README.md)
