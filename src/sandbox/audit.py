from __future__ import annotations

import hashlib
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path


def generate_manifest(output_dir: str, logs_dir: str) -> None:
    """Generate SHA-256 manifest of all files in output_dir."""
    os.makedirs(logs_dir, exist_ok=True)
    manifest_path = os.path.join(logs_dir, "manifest.txt")
    lines = []

    for root, _, files in os.walk(output_dir):
        for filename in sorted(files):
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, output_dir)
            sha256 = _hash_file(filepath)
            lines.append(f"{sha256}  {rel_path}")

    lines.sort(key=lambda l: l.split("  ", 1)[1])
    with open(manifest_path, "w") as f:
        f.write("\n".join(lines) + "\n" if lines else "")


def generate_metadata(
    logs_dir: str,
    task_id: str,
    exit_code: int,
    image: str,
) -> None:
    """Write task run metadata to meta.json."""
    meta = {
        "task_id": task_id,
        "exit_code": exit_code,
        "image": image,
        "node": socket.gethostname(),
        "start_time": datetime.now(timezone.utc).isoformat(),
        "job_id": os.environ.get("SLURM_JOB_ID", "unknown"),
    }
    meta_path = os.path.join(logs_dir, "meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def _hash_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
