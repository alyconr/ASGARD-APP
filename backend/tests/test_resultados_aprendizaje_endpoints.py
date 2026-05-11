"""HTTP tests for TASK-09 learning outcome CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.application.dto.resultados_aprendizaje import (
    ResultadoAprendizajeDeleteDTO,
    ResultadoAprendizajeDTO,
    ResultadoAprendizajeListDTO,
    ResultadoAprendizajePayloadDTO,
)
from src.application.services.resultados_aprendizaje import (
    ResultadoAprendizajeDuplicateError,
)
from src.domain.shared.enums import EstadoCampo
from src.interfaces.http.app import app
from src.interfaces.http.controllers.resultados_aprendizaje import (
    get_programa_resultado_service,
)


class FakeProgramaResultadoService:
    """Simple service double for learning outcome HTTP tests."""

    def __init__(self) -> None:
        """Initialize empty state."""
        self.competencia_id = uuid.uuid4()
        self.resultados: list[ResultadoAprendizajeDTO] = []

    async def list_resultados(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ResultadoAprendizajeListDTO:
        """Return stored learning outcomes."""
        return ResultadoAprendizajeListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia_id,
            resultados=self.resultados,
        )

    async def create_resultado(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        payload: ResultadoAprendizajePayloadDTO,
    ) -> ResultadoAprendizajeListDTO:
        """Create a learning outcome unless the description is duplicated."""
        if any(
            item.descripcion.lower() == payload.descripcion.lower()
            for item in self.resultados
        ):
            raise ResultadoAprendizajeDuplicateError(
                "Ya existe un resultado de aprendizaje con esta descripcion exacta "
                "en la competencia"
            )
        now = datetime.now(UTC)
        self.resultados.append(
            ResultadoAprendizajeDTO(
                id=uuid.uuid4(),
                competencia_id=competencia_id,
                codigo_resultado=payload.codigo_resultado.strip()
                if payload.codigo_resultado
                else None,
                descripcion=payload.descripcion,
                orden=len(self.resultados) + 1,
                estado=EstadoCampo.MANUAL,
                motivo_fallo_extraccion=None,
                fecha_creacion=now,
                fecha_actualizacion=now,
            )
        )
        return await self.list_resultados(referencia_id, competencia_id)

    async def update_resultado(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID,
        payload: ResultadoAprendizajePayloadDTO,
    ) -> ResultadoAprendizajeListDTO:
        """Update a learning outcome in memory."""
        now = datetime.now(UTC)
        self.resultados = [
            ResultadoAprendizajeDTO(
                id=item.id,
                competencia_id=item.competencia_id,
                codigo_resultado=(
                    payload.codigo_resultado.strip()
                    if payload.codigo_resultado
                    else None
                )
                if item.id == resultado_id
                else item.codigo_resultado,
                descripcion=payload.descripcion
                if item.id == resultado_id
                else item.descripcion,
                orden=item.orden,
                estado=item.estado,
                motivo_fallo_extraccion=item.motivo_fallo_extraccion,
                fecha_creacion=item.fecha_creacion,
                fecha_actualizacion=now if item.id == resultado_id else now,
            )
            for item in self.resultados
        ]
        return await self.list_resultados(referencia_id, competencia_id)

    async def delete_resultado(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID,
    ) -> ResultadoAprendizajeDeleteDTO:
        """Delete a learning outcome in memory."""
        self.resultados = [
            item for item in self.resultados if item.id != resultado_id
        ]
        return ResultadoAprendizajeDeleteDTO(
            referencia_id=referencia_id,
            competencia_id=competencia_id,
            resultado_id=resultado_id,
            eliminado=True,
        )


def test_resultados_endpoints_create_list_update_delete() -> None:
    """The HTTP API should expose the learning outcome CRUD contract."""
    fake_service = FakeProgramaResultadoService()
    app.dependency_overrides[get_programa_resultado_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()
    competencia_id = uuid.uuid4()

    create_response = client.post(
        f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}/resultados",
        json={
            "codigo_resultado": " RAP-01 ",
            "descripcion": " Analizar los requisitos del software ",
        },
    )
    resultado_id = create_response.json()["resultados"][0]["id"]
    list_response = client.get(
        f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}/resultados"
    )
    update_response = client.put(
        (
            f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
            f"/resultados/{resultado_id}"
        ),
        json={
            "codigo_resultado": "RAP-02",
            "descripcion": "Disenar la solucion de software",
        },
    )
    delete_response = client.delete(
        (
            f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
            f"/resultados/{resultado_id}"
        )
    )

    app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["referencia_id"] == str(referencia_id)
    assert create_response.json()["competencia_id"] == str(competencia_id)
    assert create_response.json()["resultados"][0]["descripcion"] == (
        "Analizar los requisitos del software"
    )
    assert create_response.json()["resultados"][0]["codigo_resultado"] == "RAP-01"
    assert list_response.status_code == 200
    assert len(list_response.json()["resultados"]) == 1
    assert update_response.status_code == 200
    assert update_response.json()["resultados"][0]["codigo_resultado"] == "RAP-02"
    assert delete_response.status_code == 200
    assert delete_response.json()["eliminado"] is True


def test_resultados_endpoint_rejects_duplicate_description() -> None:
    """The HTTP API should map duplicate descriptions to conflict responses."""
    fake_service = FakeProgramaResultadoService()
    app.dependency_overrides[get_programa_resultado_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()
    competencia_id = uuid.uuid4()

    client.post(
        f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}/resultados",
        json={"descripcion": "Analizar requisitos"},
    )
    response = client.post(
        f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}/resultados",
        json={"descripcion": "Analizar requisitos"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ya existe un resultado de aprendizaje con esta descripcion exacta "
        "en la competencia"
    )
