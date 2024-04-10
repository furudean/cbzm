import argparse
from collections.abc import Sized
from pathlib import Path
from os.path import splitext
import sys
from typing import Any
import zipfile

from colorama import Fore, init as colorama_init

from .signal import interrupthandler

compression_map = {
    "store": zipfile.ZIP_STORED,
    "deflate": zipfile.ZIP_DEFLATED,
    "bzip2": zipfile.ZIP_BZIP2,
    "lzma": zipfile.ZIP_LZMA,
}


def pl(value: int | Sized) -> str:
    """
    get plural suffix for a value
    """
    if not isinstance(value, int):
        value = len(value)

    return "s" if value != 1 else ""


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
    colorama_init(autoreset=True)

    try:
        args = parse_args()

        if args.output.is_dir():
            print(
                f"{Fore.RED}error: output file {quote_path(args.output)} is a directory"
            )
            sys.exit(1)

        if args.output.is_file() and not args.y:
            with interrupthandler(immediate=True) as h:
                while not h.interrupted:
                    response = (
                        input(
                            f"{Fore.YELLOW}output file {quote_path(args.output)} already exists!{Fore.RESET}"
                            f" overwrite? (y/n) "
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
                    print(
                        f"{Fore.RED}error: {quote_path(archive_path.resolve())} is not a file"
                    )
                    args.output.unlink(missing_ok=True)
                    sys.exit(1)

                try:
                    with zipfile.ZipFile(archive_path, mode="r") as archive:
                        page_names = archive.namelist()[args.slice]
                        removed = set(archive.namelist()) - set(page_names)

                        for page_name in page_names:
                            i += 1
                            with archive.open(page_name, "r") as f:
                                file_name = str(i).zfill(4) + splitext(page_name)[1]

                                out_file.writestr(file_name, f.read())

                        print(
                            f"{quote_path(archive_path)} → {len(page_names)} page{pl(page_names)}"
                            + (
                                f" (removed {len(removed)} page{pl(removed)})"
                                if removed
                                else ""
                            )
                        )
                except zipfile.BadZipFile:
                    print(
                        f"{Fore.RED}error: {quote_path(archive_path)} is not a valid zip file"
                    )
                    args.output.unlink(missing_ok=True)
                    sys.exit(1)

        print()

        if i == 0:
            print(f"{Fore.RED}error: no pages to add")
            args.output.unlink(missing_ok=True)
            sys.exit(1)

        print(
            f"created archive of {i} pages as{Fore.RESET} {quote_path(args.output.resolve())}"
        )

    except (KeyboardInterrupt, EOFError):
        sys.exit(130)
