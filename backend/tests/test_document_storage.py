"""Tests for document storage metadata handling."""

from src.infrastructure.storage.document_storage import build_pdf_metadata


def test_pdf_metadata_encodes_non_ascii_filename_for_s3_headers() -> None:
    """MinIO user metadata values must be US-ASCII header values."""
    metadata = build_pdf_metadata(
        original_filename="Programa de Formaci\u00f3n ADSO.pdf",
        checksum_sha256="abc123",
    )

    for value in metadata.values():
        value.encode("us-ascii")

    assert metadata["original-filename"] == "Programa%20de%20Formaci%C3%B3n%20ADSO.pdf"
    assert metadata["original-filename-encoding"] == "utf-8-percent"
