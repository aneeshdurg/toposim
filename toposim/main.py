import argparse
from pathlib import Path

from . import generate
from .application import application_registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix")
    parser.add_argument("filename")
    parser.add_argument(
        "--app",
        action="store",
        default="janusgraph",
        choices=application_registry.keys(),
    )
    parser.add_argument("--subnet32", action="store", default="174")
    parser.add_argument(
        "-l",
        "--license",
        action="store",
        default=None,
        help="License file to use for tigergraph",
    )

    args = parser.parse_args()

    # Lookup application by name
    app = application_registry[args.app]()
    generate(args.prefix, args.filename, app, args.subnet32)
