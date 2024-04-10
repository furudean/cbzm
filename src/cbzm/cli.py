import argparse
from pathlib import Path
from os.path import splitext
import sys
from typing import Any
import zipfile

from .signal import interrupthandler

compression_map = {
    "store": zipfile.ZIP_STORED,
    "deflate": zipfile.ZIP_DEFLATED,
    "bzip2": zipfile.ZIP_BZIP2,
    "lzma": zipfile.ZIP_LZMA,
}


def quote_path(path: Path | str) -> str:
    if " " in str(path):
        return f'"{path}"'
    else:
        return str(path)


def slice_expression(value: str | None) -> slice:
    """
    parses a `slice()` from string, like `start:stop:step`
    """
    if value:
        parts: list[Any] = value.split(":")
        if len(parts) == 1:
            # slice(stop)
            parts = [None, parts[0]]
        # else: slice(start, stop[, step])
    else:
        # slice()
        parts = []
    return slice(*[int(p) if p else None for p in parts])


class Args(argparse.Namespace):
    inputs: list[Path]
    output: Path
    compress: str
    slice: slice
    y: bool


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        prog="cbzm",
        description="cbz merge. merge several cbz archives into a single one",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "inputs", type=Path, nargs="+", help="archives to merge, in order"
    )

    parser.add_argument("output", type=Path, help="archive to write to")

    parser.add_argument(
        "--compress",
        "-c",
        choices=compression_map.keys(),
        default="store",
        help="compression method to use for the output archive",
    )

    parser.add_argument(
        "--slice",
        "-s",
        type=slice_expression,
        default=slice(None),
        help="python slice expression for pages to pick from each archive, for example :-1",
    )

    parser.add_argument("-y", action="store_true", help="overwrite output file")

    args = Args()
    parser.parse_args(namespace=args)

    return args


def main() -> None:
    try:
        args = parse_args()

        if args.output.exists() and not args.y:
            with interrupthandler(immediate=True) as h:
                while not h.interrupted:
                    response = (
                        input(
                            f"output file {quote_path(args.output)} already exists. overwrite? [y/N] "
                        )
                        .lower()
                        .strip()
                    )

                    if response == "y":
                        print()
                        break

                    if response == "n":
                        sys.exit(0)

        with zipfile.ZipFile(
            args.output, mode="w", compression=compression_map[args.compress]
        ) as out_file:
            i = 0

            for archive_path in args.inputs:
                if not archive_path.is_file():
                    print(f"{archive_path.resolve()} is not a file")
                    args.output.unlink(missing_ok=True)
                    sys.exit(1)

                try:
                    with zipfile.ZipFile(archive_path, mode="r") as archive:
                        page_names = archive.namelist()[args.slice]

                        for page_name in page_names:
                            i += 1
                            with archive.open(page_name, "r") as f:
                                file_name = str(i).zfill(4) + splitext(page_name)[1]

                                buffer = f.read()
                                out_file.writestr(file_name, buffer)

                        print(
                            f"{quote_path(archive_path)} → {len(page_names)} page"
                            + ("s" if len(page_names) > 1 else "")
                        )
                except zipfile.BadZipFile:
                    print(f"{quote_path(archive_path)} is not a valid zip file")
                    args.output.unlink(missing_ok=True)
                    sys.exit(1)

        print(f"\ncreated archive of {i} pages as {quote_path(args.output.resolve())}")

    except (KeyboardInterrupt, EOFError):
        sys.exit(130)
