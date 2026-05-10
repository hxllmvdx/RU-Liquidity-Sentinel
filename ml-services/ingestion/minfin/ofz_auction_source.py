from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RawSource:
    section_code: str
    section_name: str
    source_type: str
    title: str
    detail_url: str
    source_url: str
    content: bytes
    local_path: Path
