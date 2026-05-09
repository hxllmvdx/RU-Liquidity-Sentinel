from __future__ import annotations

import csv
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


def _flatten_for_csv(record: dict) -> dict[str, str | int | float | None]:
    flattened: dict[str, str | int | float | None] = {}
    for key, value in record.items():
        if isinstance(value, (dict, list)):
            flattened[key] = json.dumps(value, ensure_ascii=False)
        else:
            flattened[key] = value
    return flattened


def write_csv_atomic(
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
            normalized = [_flatten_for_csv(record.to_dict()) for record in records]
            line_count = len(normalized)
            fieldnames: list[str] = []
            for item in normalized:
                for key in item.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)

            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for item in normalized:
                writer.writerow(item)
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    temp_path.replace(output_path)
    LOGGER.info("wrote %s records to %s", line_count, output_path)
    return output_path


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
        line_count = 0
        try:
            for record in records:
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                line_count += 1
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    temp_path.replace(output_path)
    LOGGER.info("wrote %s jsonl records to %s", line_count, output_path)
    return output_path
