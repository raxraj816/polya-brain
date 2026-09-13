"""Reduced reproduction of PySnooper bug 3 at e21a3116."""

from pathlib import Path
from typing import TextIO


def get_write_function(output: Path | str | TextIO):
    if isinstance(output, (Path, str)):

        def write(value: str) -> None:
            with open(output_path, "a") as output_file:  # noqa: F821
                output_file.write(value)

        return write
    return output.write
