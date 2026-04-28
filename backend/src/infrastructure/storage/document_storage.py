"""Document storage abstraction and S3-compatible implementation."""

from __future__ import annotations

import hashlib
import io
from typing import Protocol
from urllib.parse import quote

import anyio
from minio import Minio

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.infrastructure.config.settings import Settings

PDF_METADATA_FILENAME_ENCODING = "utf-8-percent"


class DocumentStorageService(Protocol):
    """Storage port used by application services for PDF documents."""

    async def save_pdf(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> StoredDocumentDTO:
        """Store a PDF and return durable object metadata."""


class MinioDocumentStorageService:
    """S3-compatible document storage backed by MinIO."""

    def __init__(self, settings: Settings) -> None:
        """Create a MinIO client from application settings."""
        self._bucket_name = settings.storage_bucket_name
        self._region = settings.storage_region or None
        self._client = Minio(
            endpoint=settings.storage_endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            secure=settings.storage_secure,
            region=self._region,
        )

    async def save_pdf(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> StoredDocumentDTO:
        """Ensure the bucket exists, upload the PDF and return metadata."""
        checksum = hashlib.sha256(content).hexdigest()

        def upload() -> StoredDocumentDTO:
            self._ensure_bucket()
            result = self._client.put_object(
                bucket_name=self._bucket_name,
                object_name=key,
                data=io.BytesIO(content),
                length=len(content),
                content_type=content_type,
                metadata=build_pdf_metadata(
                    original_filename=original_filename,
                    checksum_sha256=checksum,
                ),
            )
            return StoredDocumentDTO(
                original_filename=original_filename,
                storage_key=key,
                size_bytes=len(content),
                content_type=content_type,
                checksum_sha256=checksum,
                etag=result.etag,
            )

        return await anyio.to_thread.run_sync(upload)

    def _ensure_bucket(self) -> None:
        """Create the configured bucket on first use when it is missing."""
        if self._client.bucket_exists(self._bucket_name):
            return

        self._client.make_bucket(self._bucket_name, location=self._region)


def build_pdf_metadata(
    *,
    original_filename: str,
    checksum_sha256: str,
) -> dict[str, str | list[str] | tuple[str]]:
    """Build S3-compatible user metadata for a PDF object."""
    return {
        "original-filename": quote(original_filename, safe=""),
        "original-filename-encoding": PDF_METADATA_FILENAME_ENCODING,
        "checksum-sha256": checksum_sha256,
    }
