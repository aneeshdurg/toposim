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
        default=None,
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

    generate(args.prefix, args.filename, args.app, args.subnet32)
