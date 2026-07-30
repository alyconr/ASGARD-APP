"""Tests for ProyectoCargueService delete functionality."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.proyecto_cargue import ProyectoCargueService
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.proyecto import ProyectoFormativo


@pytest.mark.anyio
async def test_eliminar_cargue_completo_resets_drafts_and_deletes_records() -> None:
    # Arrange
    referencia_id = uuid.uuid4()
    programa_id = uuid.uuid4()
    programa_pdf_key = (
        "programas/analisis-228118-1/documentos/programa-formacion.pdf"
    )
    proyecto_excel_key = (
        "proyectos-formativos/proyecto-test-pr-001/excel/matriz.xlsx"
    )

    # Mock session
    session = AsyncMock()
    session.add = MagicMock()

    # Mock drafts
    draft_programa = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="revision-programa",
        payload_json={
            "curricular": {"programa_formacion_id": str(programa_id)},
            "documental": {
                "programa_pdf": {
                    "documento": {"storage_key": programa_pdf_key}
                }
            },
        },
        estado_borrador=EstadoBloque.COMPLETO,
    )
    draft_proyecto = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROYECTO.value,
        referencia_id=referencia_id,
        paso_actual="revision-proyecto",
        payload_json={
            "meta": {"programaId": str(programa_id)},
            "documental": {
                "fuente_estructurada": {
                    "documento": {"storage_key": proyecto_excel_key}
                }
            },
        },
        estado_borrador=EstadoBloque.COMPLETO,
    )

    # Mock database entities
    programa_db = ProgramaFormacion(
        codigo_programa="228118",
        nombre_programa="Analisis de software",
    )
    proyecto_db = ProyectoFormativo(
        programa_id=programa_id,
        codigo_proyecto="PR-001",
        nombre_proyecto="Proyecto test",
        version_proyecto="1",
    )

    # Configure session mocks
    mock_execute_result_prog = MagicMock()
    mock_execute_result_prog.scalar_one_or_none.return_value = draft_programa

    mock_execute_result_proj = MagicMock()
    mock_execute_result_proj.scalar_one_or_none.return_value = draft_proyecto

    mock_execute_result_proyecto_db = MagicMock()
    mock_execute_result_proyecto_db.scalars.return_value.all.return_value = [
        proyecto_db
    ]

    # session.execute calls
    session.execute.side_effect = [
        mock_execute_result_prog,  # select draft programa
        mock_execute_result_proj,  # select draft proyecto
        mock_execute_result_proyecto_db,  # select ProyectoFormativo
    ]

    # session.get for ProgramaFormacion
    session.get.return_value = programa_db

    # Mock MinIO storage service
    storage_service = AsyncMock()

    service = ProyectoCargueService(session=session, storage_service=storage_service)

    # Act
    await service.eliminar_cargue_completo(referencia_id)

    # Assert
    # Verify entity deletions
    session.delete.assert_any_call(proyecto_db)
    session.delete.assert_any_call(programa_db)

    # Verify draft reset states
    assert draft_programa.paso_actual == "origen-documental"
    assert draft_programa.estado_borrador == EstadoBloque.BORRADOR
    assert draft_programa.payload_json["curricular"] == {}

    assert draft_proyecto.paso_actual == "fuente-proyecto"
    assert draft_proyecto.estado_borrador == EstadoBloque.BLOQUEADO
    assert draft_proyecto.payload_json["meta"]["programaId"] == str(programa_id)

    # Verify MinIO deletions
    storage_service.delete_by_prefix.assert_any_call(
        prefix=programa_pdf_key
    )
    storage_service.delete_by_prefix.assert_any_call(
        prefix=proyecto_excel_key
    )
    storage_service.delete_by_prefix.assert_any_call(
        prefix=f"programas/{referencia_id}/"
    )
    storage_service.delete_by_prefix.assert_any_call(
        prefix=f"proyectos-formativos/{referencia_id}/"
    )


@pytest.mark.anyio
async def test_eliminar_cargue_proyecto_preserves_program() -> None:
    # Arrange
    referencia_id = uuid.uuid4()
    programa_id = uuid.uuid4()
    proyecto_pdf_key = (
        "proyectos-formativos/proyecto-test-pr-001/documentos/proyecto-formativo.pdf"
    )

    # Mock session
    session = AsyncMock()
    session.add = MagicMock()

    # Mock project draft
    draft_proyecto = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROYECTO.value,
        referencia_id=referencia_id,
        paso_actual="revision-proyecto",
        payload_json={
            "meta": {
                "referenciaId": str(referencia_id),
                "programaReferenciaId": str(uuid.uuid4()),
                "programaId": str(programa_id),
            },
            "proyecto": {
                "proyecto_formativo_id": str(uuid.uuid4()),
                "codigo_proyecto": "PR-001",
                "nombre_proyecto": "Proyecto test",
            },
            "documental": {
                "proyecto_pdf": {
                    "documento": {"storage_key": proyecto_pdf_key}
                }
            },
        },
        estado_borrador=EstadoBloque.BORRADOR,
    )

    # Mock database project entity
    proyecto_db = ProyectoFormativo(
        programa_id=programa_id,
        codigo_proyecto="PR-001",
        nombre_proyecto="Proyecto test",
        version_proyecto="1",
    )

    # Configure session mocks
    mock_execute_result_proj = MagicMock()
    mock_execute_result_proj.scalar_one_or_none.return_value = draft_proyecto

    mock_execute_result_proyecto_db = MagicMock()
    mock_execute_result_proyecto_db.scalar_one_or_none.return_value = proyecto_db

    # session.execute calls
    session.execute.side_effect = [
        mock_execute_result_proj,  # select draft proyecto
        mock_execute_result_proyecto_db,  # select ProyectoFormativo
    ]

    # Mock MinIO storage service
    storage_service = AsyncMock()

    service = ProyectoCargueService(session=session, storage_service=storage_service)

    # Act
    await service.eliminar_cargue_proyecto(referencia_id)

    # Assert
    # Verify project deletion but NO program deletion
    session.delete.assert_called_once_with(proyecto_db)

    # Verify draft project reset states
    assert draft_proyecto.paso_actual == "fuente-proyecto"
    assert draft_proyecto.estado_borrador == EstadoBloque.BORRADOR
    assert draft_proyecto.payload_json["proyecto"]["proyecto_formativo_id"] is None
    assert draft_proyecto.payload_json["documental"]["proyecto_pdf"] is None

    # Verify MinIO project deletions only
    storage_service.delete_by_prefix.assert_any_call(
        prefix=proyecto_pdf_key
    )
    storage_service.delete_by_prefix.assert_any_call(
        prefix=f"proyectos-formativos/{referencia_id}/"
    )
    # Ensure program prefixes were NOT deleted
    for call in storage_service.delete_by_prefix.call_args_list:
        assert "programas/" not in call.kwargs.get("prefix", "")
