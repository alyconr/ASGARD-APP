"""HTTP tests for TASK-08 competence CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.application.dto.competencias import (
    CompetenciaDeleteDTO,
    CompetenciaDTO,
    CompetenciaListDTO,
    CompetenciaPayloadDTO,
)
from src.application.services.competencias import CompetenciaDuplicateCodeError
from src.domain.shared.enums import EstadoBloque, EstadoCampo
from src.interfaces.http.app import app
from src.interfaces.http.controllers.competencias import (
    get_programa_competencia_service,
)


class FakeProgramaCompetenciaService:
    """Simple service double for competence HTTP tests."""

    def __init__(self) -> None:
        """Initialize empty state."""
        self.programa_id = uuid.uuid4()
        self.competencias: list[CompetenciaDTO] = []

    async def list_competencias(self, referencia_id: uuid.UUID) -> CompetenciaListDTO:
        """Return stored competences."""
        return CompetenciaListDTO(
            referencia_id=referencia_id,
            programa_id=self.programa_id,
            competencias=self.competencias,
        )

    async def create_competencia(
        self,
        referencia_id: uuid.UUID,
        payload: CompetenciaPayloadDTO,
    ) -> CompetenciaListDTO:
        """Create a competence unless code is duplicated."""
        if any(
            item.codigo_competencia.lower() == payload.codigo_competencia.lower()
            for item in self.competencias
        ):
            raise CompetenciaDuplicateCodeError(
                "Ya existe una competencia con ese codigo en el programa actual"
            )
        now = datetime.now(UTC)
        self.competencias.append(
            CompetenciaDTO(
                id=uuid.uuid4(),
                programa_id=self.programa_id,
                codigo_competencia=payload.codigo_competencia,
                nombre_competencia=payload.nombre_competencia,
                orden=len(self.competencias) + 1,
                estado=EstadoBloque.BORRADOR,
                origen_campo=EstadoCampo.MANUAL,
                fecha_creacion=now,
                fecha_actualizacion=now,
            )
        )
        return await self.list_competencias(referencia_id)

    async def update_competencia(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        payload: CompetenciaPayloadDTO,
    ) -> CompetenciaListDTO:
        """Update a competence in memory."""
        now = datetime.now(UTC)
        self.competencias = [
            CompetenciaDTO(
                id=item.id,
                programa_id=item.programa_id,
                codigo_competencia=payload.codigo_competencia
                if item.id == competencia_id
                else item.codigo_competencia,
                nombre_competencia=payload.nombre_competencia
                if item.id == competencia_id
                else item.nombre_competencia,
                orden=item.orden,
                estado=item.estado,
                origen_campo=item.origen_campo,
                fecha_creacion=item.fecha_creacion,
                fecha_actualizacion=now if item.id == competencia_id else now,
            )
            for item in self.competencias
        ]
        return await self.list_competencias(referencia_id)

    async def delete_competencia(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> CompetenciaDeleteDTO:
        """Delete a competence in memory."""
        self.competencias = [
            item for item in self.competencias if item.id != competencia_id
        ]
        return CompetenciaDeleteDTO(
            referencia_id=referencia_id,
            programa_id=self.programa_id,
            competencia_id=competencia_id,
            eliminado=True,
        )


def test_competencias_endpoints_create_list_update_delete() -> None:
    """The HTTP API should expose the competence CRUD contract."""
    fake_service = FakeProgramaCompetenciaService()
    app.dependency_overrides[get_programa_competencia_service] = (
        lambda: fake_service
    )
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    create_response = client.post(
        f"/api/v1/programas/{referencia_id}/competencias",
        json={
            "codigo_competencia": " 220501046 ",
            "nombre_competencia": " Desarrollar software ",
        },
    )
    competencia_id = create_response.json()["competencias"][0]["id"]
    list_response = client.get(f"/api/v1/programas/{referencia_id}/competencias")
    update_response = client.put(
        f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}",
        json={
            "codigo_competencia": "220501047",
            "nombre_competencia": "Implementar soluciones de software",
        },
    )
    delete_response = client.delete(
        f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
    )

    app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["referencia_id"] == str(referencia_id)
    assert create_response.json()["competencias"][0]["codigo_competencia"] == (
        "220501046"
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["competencias"]) == 1
    assert update_response.status_code == 200
    assert update_response.json()["competencias"][0]["codigo_competencia"] == (
        "220501047"
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["eliminado"] is True


def test_competencias_endpoint_rejects_duplicate_code() -> None:
    """The HTTP API should map duplicate codes to conflict responses."""
    fake_service = FakeProgramaCompetenciaService()
    app.dependency_overrides[get_programa_competencia_service] = (
        lambda: fake_service
    )
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    client.post(
        f"/api/v1/programas/{referencia_id}/competencias",
        json={
            "codigo_competencia": "220501046",
            "nombre_competencia": "Desarrollar software",
        },
    )
    response = client.post(
        f"/api/v1/programas/{referencia_id}/competencias",
        json={
            "codigo_competencia": "220501046",
            "nombre_competencia": "Implementar software",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ya existe una competencia con ese codigo en el programa actual"
    )
