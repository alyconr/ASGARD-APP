"""HTTP tests for TASK-14 program completion and close endpoints."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from src.application.dto.programa_cierre import (
    ProgramaCierreDTO,
    ProgramaCompletitudDTO,
    ProgramaCompletitudFaltanteDTO,
    ProgramaCompletitudResumenDTO,
)
from src.application.services.programa_cierre import ProgramaCierreValidationError
from src.domain.shared.enums import EstadoBloque
from src.interfaces.http.app import app
from src.interfaces.http.controllers.programa_cierre import get_programa_cierre_service


class FakeProgramaCierreService:
    """Simple service double for program close HTTP tests."""

    def __init__(self, *, cerrable: bool) -> None:
        """Store the validation outcome."""
        self.cerrable = cerrable
        self.programa_id = uuid.uuid4()

    async def validar_completitud(
        self,
        referencia_id: uuid.UUID,
    ) -> ProgramaCompletitudDTO:
        """Return a deterministic validation result."""
        faltantes = (
            []
            if self.cerrable
            else [
                ProgramaCompletitudFaltanteDTO(
                    codigo="programa.competencias",
                    campo="competencias",
                    mensaje="Registra al menos una competencia asociada al programa.",
                )
            ]
        )
        return ProgramaCompletitudDTO(
            referencia_id=referencia_id,
            programa_id=self.programa_id,
            estado_actual=EstadoBloque.BORRADOR,
            cerrable=self.cerrable,
            resumen=ProgramaCompletitudResumenDTO(
                competencias=1 if self.cerrable else 0,
                resultados=1 if self.cerrable else 0,
                conocimientos_saber=1 if self.cerrable else 0,
                conocimientos_proceso=1 if self.cerrable else 0,
                criterios=1 if self.cerrable else 0,
            ),
            faltantes=faltantes,
        )

    async def cerrar_programa(self, referencia_id: uuid.UUID) -> ProgramaCierreDTO:
        """Close or reject based on the configured validation result."""
        completitud = await self.validar_completitud(referencia_id)
        if not self.cerrable:
            raise ProgramaCierreValidationError(completitud)
        return ProgramaCierreDTO(
            referencia_id=referencia_id,
            programa_id=self.programa_id,
            estado=EstadoBloque.COMPLETO,
            mensaje="Programa cerrado correctamente.",
            completitud=ProgramaCompletitudDTO(
                referencia_id=referencia_id,
                programa_id=self.programa_id,
                estado_actual=EstadoBloque.COMPLETO,
                cerrable=True,
                resumen=completitud.resumen,
                faltantes=[],
            ),
        )


def test_completitud_endpoint_returns_structured_missing_items() -> None:
    """The validation endpoint should expose structured missing requirements."""
    fake_service = FakeProgramaCierreService(cerrable=False)
    app.dependency_overrides[get_programa_cierre_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.get(f"/api/v1/programas/{referencia_id}/completitud")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cerrable"] is False
    assert response.json()["faltantes"][0]["campo"] == "competencias"


def test_cierre_endpoint_rejects_incomplete_program() -> None:
    """The close endpoint should reject incomplete programs with detail payload."""
    fake_service = FakeProgramaCierreService(cerrable=False)
    app.dependency_overrides[get_programa_cierre_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.post(f"/api/v1/programas/{referencia_id}/cierre")

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"]["cerrable"] is False
    assert response.json()["detail"]["faltantes"][0]["campo"] == "competencias"


def test_cierre_endpoint_returns_completed_state() -> None:
    """The close endpoint should return COMPLETO when validation passes."""
    fake_service = FakeProgramaCierreService(cerrable=True)
    app.dependency_overrides[get_programa_cierre_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.post(f"/api/v1/programas/{referencia_id}/cierre")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["estado"] == "COMPLETO"
    assert response.json()["completitud"]["cerrable"] is True
