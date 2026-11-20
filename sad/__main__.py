import argparse
import sys
from pathlib import Path

from .compiler import compile_file
from .errors import SadError
from .transformers import TRANSFORMERS


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sad", description="Compile a Structure-as-Directory tree into one file.")
    parser.add_argument("root", type=Path, help="the directory to compile")
    parser.add_argument("transformer", choices=sorted(TRANSFORMERS), help="the format of the files and the output")
    parser.add_argument("output", type=Path, help="the file to write")
    args = parser.parse_args(argv)
    try:
        compile_file(args.root, args.transformer, args.output)
    except SadError as exc:
        print(f"sad: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
