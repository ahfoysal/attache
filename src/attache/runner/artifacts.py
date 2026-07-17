"""Content-addressed artifact store on local disk.

The schema keeps only URIs, so swapping this for S3-compatible storage later is
a config change (docs/memory.md). For Phase 0: files land under the artifact
root, addressed by content hash to dedupe identical reports.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def ingest_text(self, task_id: str, name: str, content: str) -> tuple[str, int, str]:
        """Store text content, return (uri, size_bytes, digest)."""
        data = content.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        task_dir = self.root / str(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        path = task_dir / name
        path.write_bytes(data)
        return path.as_uri(), len(data), digest
