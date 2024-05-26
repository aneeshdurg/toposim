import os
from contextlib import contextmanager


@contextmanager
def print_to_file(filename: str):
    with open(filename, "w") as f:

        def output(*args, **kwargs):
            print(*args, **kwargs)
            print(*args, **kwargs, file=f)

        yield output


@contextmanager
def print_to_script(filename: str):
    with print_to_file(filename) as output:
        output("#!/bin/bash")
        yield output
    os.system(f"chmod +x {filename}")
