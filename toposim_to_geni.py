"""An example of constructing a profile with install and execute services.

Instructions:
Wait for the profile instance to start, then click on the node in the topology
and choose the `shell` menu item. The install and execute services are handled
automatically during profile instantiation, with no manual intervention required.
"""

# Import the Portal object.
import geni.portal as portal

# Import the ProtoGENI library.
import geni.rspec.pg as rspec

# Create a Request object to start building the RSpec.
request = portal.context.makeRequestRSpec()

def create_toposim_node(request):
    # Add a raw PC to the request.
    node = request.RawPC("node")

    # Request that a specific image be installed on this node
    node.disk_image = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU24-64-BETA"

    node.addService(
        rspec.Install(
            url="https://github.com/aneeshdurg/toposim/archive/refs/heads/main.tar.gz",
            path="/toposim",
        )
    )
    node.addService(rspec.Execute(shell="bash", command="/toposim/toposim-main/cloudlab/setup.sh arg0"))
    return node

create_toposim_node(request)

portal.context.printRequestRSpec()
