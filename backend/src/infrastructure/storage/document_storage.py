"""Document storage abstraction and S3-compatible implementation."""

from __future__ import annotations

import hashlib
import io
from typing import Protocol
from urllib.parse import quote

import anyio
from minio import Minio
from minio.error import S3Error

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.infrastructure.config.settings import Settings

PDF_METADATA_FILENAME_ENCODING = "utf-8-percent"


class DocumentStorageService(Protocol):
    """Storage port used by application services for program documents."""

    async def save_pdf(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> StoredDocumentDTO:
        """Store a PDF and return durable object metadata."""

    async def read_pdf(self, *, key: str) -> bytes:
        """Read a stored PDF object by key."""

    async def save_excel(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> StoredDocumentDTO:
        """Store a canonical Excel workbook and return durable metadata."""

    async def read_excel(self, *, key: str) -> bytes:
        """Read a stored Excel workbook by key."""

    async def delete_by_prefix(self, *, prefix: str) -> None:
        """Remove all objects matching the prefix from the bucket."""


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

    async def read_pdf(self, *, key: str) -> bytes:
        """Read a stored PDF object by key."""

        return await self._read_object(key=key, missing_label="PDF")

    async def save_excel(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> StoredDocumentDTO:
        """Ensure the bucket exists, upload the workbook and return metadata."""
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

    async def read_excel(self, *, key: str) -> bytes:
        """Read a stored Excel object by key."""

        return await self._read_object(key=key, missing_label="Excel")

    async def _read_object(self, *, key: str, missing_label: str) -> bytes:
        """Read a stored object by key."""

        def download() -> bytes:
            try:
                response = self._client.get_object(
                    bucket_name=self._bucket_name,
                    object_name=key,
                )
            except S3Error as error:
                if error.code in {"NoSuchKey", "NoSuchBucket"}:
                    raise FileNotFoundError(
                        f"No existe el {missing_label} almacenado con key {key}",
                    ) from error
                raise

            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await anyio.to_thread.run_sync(download)

    def _ensure_bucket(self) -> None:
        """Create the configured bucket on first use when it is missing."""
        if self._client.bucket_exists(self._bucket_name):
            return

        self._client.make_bucket(self._bucket_name, location=self._region)

    async def delete_by_prefix(self, *, prefix: str) -> None:
        """Remove all objects matching the given prefix from the bucket."""

        def remove() -> None:
            self._ensure_bucket()
            objects_to_delete = self._client.list_objects(
                bucket_name=self._bucket_name,
                prefix=prefix,
                recursive=True,
            )
            for obj in objects_to_delete:
                self._client.remove_object(self._bucket_name, obj.object_name)

        await anyio.to_thread.run_sync(remove)


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
