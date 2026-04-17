"""Tests for GCS database loader with mocked GCS client."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pillcare.gcs_loader import download_db, compute_sha256


@pytest.fixture
def valid_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO test VALUES (1)")
    conn.commit()
    conn.close()
    return db_path


def test_compute_sha256(valid_db: Path):
    sha = compute_sha256(str(valid_db))
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)


@patch("pillcare.gcs_loader.storage")
def test_download_db_success(mock_storage, valid_db: Path, tmp_path: Path):
    local_path = str(tmp_path / "downloaded.db")
    expected_sha = compute_sha256(str(valid_db))

    mock_client = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    def fake_download(path):
        import shutil

        shutil.copy2(str(valid_db), path)

    mock_blob.download_to_filename.side_effect = fake_download

    result = download_db(
        "test-bucket", "test.db", local_path, expected_sha256=expected_sha
    )
    assert result == local_path
    assert Path(local_path).exists()


@patch("pillcare.gcs_loader.storage")
def test_download_db_sha_mismatch(mock_storage, valid_db: Path, tmp_path: Path):
    local_path = str(tmp_path / "downloaded.db")

    mock_client = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    def fake_download(path):
        import shutil

        shutil.copy2(str(valid_db), path)

    mock_blob.download_to_filename.side_effect = fake_download

    with pytest.raises(RuntimeError, match="DB integrity.*SHA256"):
        download_db("test-bucket", "test.db", local_path, expected_sha256="wrong_hash")


@patch("pillcare.gcs_loader.storage")
def test_download_db_no_sha_check(mock_storage, valid_db: Path, tmp_path: Path):
    local_path = str(tmp_path / "downloaded.db")

    mock_client = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    def fake_download(path):
        import shutil

        shutil.copy2(str(valid_db), path)

    mock_blob.download_to_filename.side_effect = fake_download

    result = download_db("test-bucket", "test.db", local_path)
    assert result == local_path


@patch("pillcare.gcs_loader.storage")
def test_download_db_network_error(mock_storage, tmp_path: Path):
    """download_db raises on network error."""
    local_path = str(tmp_path / "downloaded.db")

    mock_client = MagicMock()
    mock_storage.Client.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_to_filename.side_effect = Exception("Network error")

    with pytest.raises(Exception, match="Network error"):
        download_db("test-bucket", "test.db", local_path)
