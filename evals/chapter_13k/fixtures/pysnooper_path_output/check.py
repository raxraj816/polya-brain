from pathlib import Path
from types import ModuleType


def verify(implementation: ModuleType) -> None:
    output = Path(__file__).with_name("reproduction-output.txt")
    output.unlink(missing_ok=True)
    try:
        writer = implementation.get_write_function(output)
        writer("trace-line")
        assert output.read_text(encoding="utf-8") == "trace-line"
    finally:
        output.unlink(missing_ok=True)
