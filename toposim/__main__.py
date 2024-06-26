import sys
import argparse

from . import generate
from .application import JanusGraphOnCassandra, TigerGraph

parser = argparse.ArgumentParser()
parser.add_argument("prefix")
parser.add_argument("filename")
parser.add_argument("--app", action="store", default="janusgraph")
parser.add_argument("--subnet32", action="store", default="174")

args = parser.parse_args()

if args.app == "janusgraph":
    app = JanusGraphOnCassandra()
elif args.app == "tigergraph":
    app = TigerGraph()
else:
    raise Exception("unknown app type")
generate(args.prefix, args.filename, app, args.subnet32)
