from __future__ import annotations

from pathlib import Path
import json
import logging
import os
import tempfile
from typing import Iterable, Protocol


LOGGER = logging.getLogger(__name__)


class SupportsToDict(Protocol):
    def to_dict(self) -> dict:
        ...


def write_jsonl_atomic(
    records: Iterable[SupportsToDict],
    output_path: Path,
    overwrite: bool = True,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"output file already exists: {output_path}")

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        try:
            line_count = 0
            for record in records:
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                line_count += 1
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    temp_path.replace(output_path)
    LOGGER.info("wrote %s records to %s", line_count, output_path)
    return output_path
