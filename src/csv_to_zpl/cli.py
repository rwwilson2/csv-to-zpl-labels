"""Stream a shipment CSV into ZPL labels, one row at a time."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import sys

from .label import DEFAULT_SIZE, LabelSize, MissingFieldError, render_label

GZIP_MAGIC = b"\x1f\x8b"


def _open_input(path: str) -> io.TextIOBase:
    """Open a CSV source, transparently decompressing gzip input.

    Detection is by magic bytes rather than the ".gz" extension, so it
    works regardless of file naming and also covers gzipped CSV piped
    in over stdin.
    """
    raw = sys.stdin.buffer if path == "-" else open(path, "rb")
    if raw.peek(2)[:2] == GZIP_MAGIC:
        raw = gzip.GzipFile(fileobj=raw)
    return io.TextIOWrapper(raw, encoding="utf-8", newline="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-to-zpl",
        description="Convert a shipment CSV into ZPL labels, one per row.",
    )
    parser.add_argument("input", help="CSV file to read, or '-' for stdin")
    parser.add_argument(
        "-o", "--output", default="-", help="file to write ZPL to (default: stdout)"
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="skip rows missing required fields instead of aborting on the first one",
    )
    parser.add_argument(
        "--label-width",
        type=float,
        default=DEFAULT_SIZE.width_in,
        metavar="INCHES",
        help=f"label width in inches (default: {DEFAULT_SIZE.width_in})",
    )
    parser.add_argument(
        "--label-height",
        type=float,
        default=DEFAULT_SIZE.height_in,
        metavar="INCHES",
        help=f"label height in inches (default: {DEFAULT_SIZE.height_in})",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_SIZE.dpi,
        help=f"printer resolution in dots per inch (default: {DEFAULT_SIZE.dpi})",
    )
    return parser


def run(
    input_path: str,
    output_path: str,
    skip_errors: bool = False,
    size: LabelSize = DEFAULT_SIZE,
) -> int:
    in_file = _open_input(input_path)
    out_file = sys.stdout if output_path == "-" else open(output_path, "w", encoding="utf-8")

    try:
        reader = csv.DictReader(in_file)
        # csv.DictReader pulls one row at a time off the underlying file
        # iterator, and we flush after each write below, so a multi-gigabyte
        # order export never has to sit fully in memory or in an output buffer.
        had_errors = False
        for line_number, row in enumerate(reader, start=2):  # header occupies line 1
            try:
                label = render_label(row, size)
            except MissingFieldError as exc:
                print(f"{input_path}:{line_number}: {exc}", file=sys.stderr)
                if not skip_errors:
                    return 1
                had_errors = True
                continue
            out_file.write(label)
            out_file.flush()
        return 1 if had_errors else 0
    finally:
        if input_path != "-":
            in_file.close()
        if out_file is not sys.stdout:
            out_file.close()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    size = LabelSize(args.label_width, args.label_height, args.dpi)
    return run(args.input, args.output, args.skip_errors, size)


if __name__ == "__main__":
    raise SystemExit(main())
