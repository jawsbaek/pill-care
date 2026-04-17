"""Download SQLite DB from GCS with integrity verification."""

import hashlib
import os
import sqlite3
import tempfile

from google.cloud import storage


def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hex digest of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def download_db(
    bucket_name: str,
    blob_name: str,
    local_path: str,
    expected_sha256: str | None = None,
) -> str:
    """Download DB from GCS, verify integrity, atomically move to local_path."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Download to temp file first (atomic safety)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(local_path) or "/tmp", suffix=".db.part"
    )
    os.close(tmp_fd)
    try:
        blob.download_to_filename(tmp_path)

        if expected_sha256:
            actual = compute_sha256(tmp_path)
            if actual != expected_sha256:
                raise RuntimeError(
                    f"DB integrity failed: SHA256 expected {expected_sha256}, got {actual}"
                )

        conn = sqlite3.connect(tmp_path)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                raise RuntimeError(f"SQLite integrity check failed: {result[0]}")
        finally:
            conn.close()

        # Atomic rename (same filesystem)
        os.replace(tmp_path, local_path)
    except Exception:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise

    return local_path
