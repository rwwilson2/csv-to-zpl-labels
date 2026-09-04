"""Stream a shipment CSV into ZPL labels, one row at a time."""

from __future__ import annotations

import argparse
import csv
import sys

from .label import MissingFieldError, render_label


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-to-zpl",
        description="Convert a shipment CSV into ZPL labels, one per row.",
    )
    parser.add_argument("input", help="CSV file to read, or '-' for stdin")
    parser.add_argument(
        "-o", "--output", default="-", help="file to write ZPL to (default: stdout)"
    )
    return parser


def run(input_path: str, output_path: str) -> int:
    in_file = (
        sys.stdin if input_path == "-" else open(input_path, newline="", encoding="utf-8")
    )
    out_file = sys.stdout if output_path == "-" else open(output_path, "w", encoding="utf-8")

    try:
        reader = csv.DictReader(in_file)
        # csv.DictReader pulls one row at a time off the underlying file
        # iterator, and we flush after each write below, so a multi-gigabyte
        # order export never has to sit fully in memory or in an output buffer.
        for line_number, row in enumerate(reader, start=2):  # header occupies line 1
            try:
                label = render_label(row)
            except MissingFieldError as exc:
                print(f"{input_path}:{line_number}: {exc}", file=sys.stderr)
                return 1
            out_file.write(label)
            out_file.flush()
        return 0
    finally:
        if in_file is not sys.stdin:
            in_file.close()
        if out_file is not sys.stdout:
            out_file.close()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return run(args.input, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
