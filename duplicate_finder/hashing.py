"""Content fingerprints used to compare files.

BLAKE2b is used because it is faster than SHA-256 in CPython while being
just as collision resistant for this purpose.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # 1 MiB
PARTIAL_SIZE = 64 * 1024  # 64 KiB: enough to tell most different files apart


def partial_digest(path: Path) -> str:
    """Fingerprint of the first PARTIAL_SIZE bytes; a cheap pre-filter."""
    with open(path, "rb") as stream:
        return hashlib.blake2b(stream.read(PARTIAL_SIZE)).hexdigest()


def full_digest(path: Path) -> str:
    """Fingerprint of the whole file, read in chunks to bound memory use."""
    digest = hashlib.blake2b()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()
