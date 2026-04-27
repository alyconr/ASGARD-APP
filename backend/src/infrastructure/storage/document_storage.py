"""Document storage abstraction and S3-compatible implementation."""

from __future__ import annotations

import hashlib
import io
from typing import Protocol

import anyio
from minio import Minio

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.infrastructure.config.settings import Settings


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
                metadata={
                    "original-filename": original_filename,
                    "checksum-sha256": checksum,
                },
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
