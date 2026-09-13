"""Reduced fixed behavior from PySnooper commit 15555ed7."""

from pathlib import Path
from typing import TextIO


def get_write_function(output: Path | str | TextIO):
    if isinstance(output, (Path, str)):

        def write(value: str) -> None:
            with open(output, "a") as output_file:
                output_file.write(value)

        return write
    return output.write
