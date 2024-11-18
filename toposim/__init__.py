#!/usr/bin/env python
import json
import os
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .application import Application
from .topology import Node, Topology
from .utils import print_to_file, print_to_script


template_dir = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(template_dir))


def template(fname: str, topo: Topology) -> str:
    template_obj = env.get_template(fname)
    return template_obj.render(topo=topo)


def generate_docker_compose(app: Application, topo: Topology):
    # Set up docker-compose.yml. This could be a template as well, but getting
    # the whitespace to render correctly in templates is a bit painful, so it's
    # easier to leave this in python so that we can easily modify it.
    with print_to_file("docker-compose.yml") as output:
        output("networks:")
        for net in topo.networks:
            output(f"  {net.name}:")
            output(f"    driver: bridge")
            output(f"    ipam:")
            output(f"      config:")
            output(f"        - subnet: {net.subnet16}.0.0/16")
            output(f"          gateway: {net.subnet16}.0.1")
        output("services:")
        for p in topo.ports.values():
            output(f"  {p.name}:")
            output(f"    image: ubuntu:latest")
            output(f'    entrypoint: /bin/sh -c "sleep inf"')
            output(f"    container_name: {p.name}")
            output(f"    hostname: {p.name}")
            output(f"    cap_add:")
            output(f'      - "NET_ADMIN"')
            output(f"    networks:")
            for i, net in enumerate(p.networks):
                output(f"      {net.name}:")
                output(f"        ipv4_address: {p.ips[i]}")

        for i, node in enumerate(topo.nodes.values()):
            output(f"  {node.name}:")
            output(f"    image: {app.image(node)}")
            output(f"    container_name: {node.name}")
            output(f"    hostname: {node.name}")
            if mem_limit := app.mem_limit(node):
                output(f"    mem_limit: {mem_limit}")
            if cpus := app.cpus(node):
                output(f"    cpus: {cpus}")
            if entrypt := app.entrypoint(node):
                output(f"    entrypoint: {entrypt}")
            output(f"    networks:")
            output(f"      {node.networks[0].name}:")
            output(f"        ipv4_address: {node.ip}")
            if ports := app.ports(node):
                output(f"    ports:")
                for src, dst in ports.items():
                    output(f'      - "{src}:{dst}"')
            output(f"    cap_add:")
            output(f'      - "NET_ADMIN"')
            output(f"    volumes:")
            for src, dst in app.volumes(node).items():
                output(f"      - {src}:{dst}")
            if env := app.environment(node):
                output(f"    environment:")
                for key, val in env.items():
                    output(f'      {key}: "{val}"')
            if depends_on := app.depends_on(node):
                output("    depends_on:")
                output(f"      - {depends_on}")
        if app.should_create_volumes():
            output("volumes:")
            for i, node in enumerate(topo.nodes.values()):
                for src, dst in app.volumes(node).items():
                    output(f"    {src}:")
                    output(f"        external: false")


def generate(prefix: str, filename: str, app: Application, subnet32: str):
    with open(filename) as f:
        data = json.load(f)
    os.makedirs(prefix, exist_ok=True)
    shutil.copy(filename, f"{prefix}/topology.json")
    os.chdir(prefix)

    names = set(data["links"].keys())
    nodes = {}
    i = 0
    for k, links in data["links"].items():
        for l in links:
            if l not in names:
                raise Exception(f"Unknown node {l}")
            assert k in data["links"][l], f"malformed link {k} -> {l}"
        name = f"{prefix}_{k}"
        print(name, name in data["dummyNodes"])
        nodes[name] = Node(
            name, [f"{prefix}_{l}" for l in links], k in data["dummyNodes"]
        )
        i += 1

    topo = Topology(prefix, nodes, subnet32=subnet32)

    app.initialize(topo)
    generate_docker_compose(app, topo)
    app.extra(topo)

    os.makedirs("tools", exist_ok=True)
    templates = [
        "add_delay",
        "cleanup",
        "mod_delay",
        "resume",
        "tools/collect_queue_depth",
        "tools/egress",
        "tools/get_mac",
        "tools/limit_bandwidth",
        "tools/run_in_ns",
        "tools/tcpdump",
    ]
    for t in templates:
        with print_to_script(f"{t}") as output:
            output(template(f"{t}.sh", topo))

    # pause and setup_networking are special cases, since there might be
    # application specific behavior we need to inject
    with print_to_script("setup_networking") as output:
        output(template("setup_networking.sh", topo))
        app.post_network_setup(topo, output)
        output("wait")

    with print_to_script("pause") as output:
        output(template("pause.sh", topo))
        app.post_pause(output)
