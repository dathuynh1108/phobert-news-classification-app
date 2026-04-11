from __future__ import annotations

import sys
from pathlib import Path


def normalize(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    content = content.replace("from google.protobuf import runtime_version as _runtime_version\n", "")
    block = """_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    7,
    34,
    1,
    '',
    'classifier.proto'
)
"""
    content = content.replace(block, "")
    path.write_text(content, encoding="utf-8")


def main() -> None:
    for arg in sys.argv[1:]:
        normalize(Path(arg))


if __name__ == "__main__":
    main()

