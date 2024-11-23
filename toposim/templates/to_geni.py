"""cloudlab profile created with toposim for {{topo.prefix}} """

# Import the Portal object.
import geni.portal as portal

# Import the ProtoGENI library.
import geni.rspec.pg as rspec

# Create a Request object to start building the RSpec.
request = portal.context.makeRequestRSpec()

def create_toposim_node(request, hostname, args: list[str] | None=None):
    if args is None:
        args = []
    # Add a raw PC to the request.
    node = request.RawPC(hostname)
    args += ["--hostname", f"{hostname}"]

    # Request that a specific image be installed on this node
    node.disk_image = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU24-64-BETA"

    node.addService(
        rspec.Install(
            url="https://github.com/aneeshdurg/toposim/archive/refs/heads/main.tar.gz",
            path="/toposim",
        )
    )
    node.addService(rspec.Execute(
        shell="bash",
        command=f"/toposim/toposim-main/cloudlab/setup.sh {' '.join(args)}"
    ))
    return node

nodes = {}
# Define all compute nodes
{%- for n in topo.nodes +%}
nodes["{{n}}"] = create_toposim_node(request, "{{n}}")
{%- endfor %}
# Define all forwarding nodes
{%- for p in topo.ports.values() +%}
nodes["{{p.name}}"] = create_toposim_node(request, "{{p.name}}", ["--dummy"])
{%- endfor %}

def getip(addr):
    return rspec.IPv4Address(addr, "255.255.0.0")


{%- for net in topo.networks +%}
# NET {{net.name}}
{{net.name}}_ifaces = [
    {%- for dev in net.devices %}
    nodes["{{dev}}"].addInterface(name="{{net.name}}{{dev}}", address=getip("{{net.devices[dev]}}")),
    {%- endfor %}
]
assert len({{net.name}}_ifaces) < 3
if len({{net.name}}_ifaces) == 2:
    request.Link(members={{net.name}}_ifaces)
{%- endfor %}

portal.context.printRequestRSpec()
