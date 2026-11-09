from dataclasses import dataclass


@dataclass(frozen=True)
class FileInfo:
    path: str
    name: str
    size: int
    modified: str
    extension: str
    mime: str
    hash: str
