# Galois

To load Galois in toposim, you must first locally build a Galois docker image.
To do so, navigate to this directory and run:

```bash
docker build -t galois .
```

## Running applications

All Galois binaries are available at `/Galois`. To run, you'll need to docker
exec the following from any host:

```bash
docker exec -it <container> conda run -n Galois --no-capture \
    mpi run -hostfile /home/root/data/hostfile <path to binary> <args>
```
