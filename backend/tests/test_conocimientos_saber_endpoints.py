"""HTTP tests for TASK-10 SABER knowledge CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.application.dto.conocimientos_saber import (
    ConocimientoSaberDTO,
    ConocimientoSaberListDTO,
    ConocimientoSaberPayloadDTO,
)
from src.application.services.conocimientos_saber import (
    ConocimientoSaberCompetenciaNotFoundError,
    ConocimientoSaberDuplicateError,
    ConocimientoSaberNotFoundError,
)
from src.domain.shared.enums import EstadoCampo, TipoConocimiento
from src.interfaces.http.app import app
from src.interfaces.http.controllers.conocimientos_saber import (
    get_programa_conocimiento_saber_service,
)


class FakeProgramaConocimientoSaberService:
    """Simple service double for SABER knowledge HTTP tests."""

    def __init__(self) -> None:
        """Initialize empty state."""
        self.competencia_id = uuid.uuid4()
        self.conocimientos: list[ConocimientoSaberDTO] = []

    async def list_conocimientos(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ConocimientoSaberListDTO:
        """Return stored SABER knowledge items."""
        if competencia_id != self.competencia_id:
            raise ConocimientoSaberCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        return ConocimientoSaberListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia_id,
            conocimientos=self.conocimientos,
        )

    async def create_conocimiento(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        payload: ConocimientoSaberPayloadDTO,
    ) -> ConocimientoSaberListDTO:
        """Create a SABER knowledge item unless the description is duplicated."""
        if competencia_id != self.competencia_id:
            raise ConocimientoSaberCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        if any(
            item.descripcion.lower() == payload.descripcion.lower()
            for item in self.conocimientos
        ):
            raise ConocimientoSaberDuplicateError(
                "Ya existe un conocimiento SABER con esta descripcion exacta "
                "en la competencia"
            )
        now = datetime.now(UTC)
        self.conocimientos.append(
            ConocimientoSaberDTO(
                id=uuid.uuid4(),
                competencia_id=competencia_id,
                resultado_id=None,
                tipo=TipoConocimiento.SABER,
                descripcion=payload.descripcion,
                orden=len(self.conocimientos) + 1,
                estado=EstadoCampo.MANUAL,
                fecha_creacion=now,
                fecha_actualizacion=now,
            )
        )
        return await self.list_conocimientos(referencia_id, competencia_id)

    async def update_conocimiento(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        conocimiento_id: uuid.UUID,
        payload: ConocimientoSaberPayloadDTO,
    ) -> ConocimientoSaberListDTO:
        """Update a SABER knowledge item in memory."""
        if competencia_id != self.competencia_id:
            raise ConocimientoSaberCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        if not any(item.id == conocimiento_id for item in self.conocimientos):
            raise ConocimientoSaberNotFoundError(
                "No existe el conocimiento SABER solicitado para esta competencia"
            )
        now = datetime.now(UTC)
        self.conocimientos = [
            ConocimientoSaberDTO(
                id=item.id,
                competencia_id=item.competencia_id,
                resultado_id=item.resultado_id,
                tipo=item.tipo,
                descripcion=payload.descripcion
                if item.id == conocimiento_id
                else item.descripcion,
                orden=item.orden,
                estado=item.estado,
                fecha_creacion=item.fecha_creacion,
                fecha_actualizacion=now if item.id == conocimiento_id else now,
            )
            for item in self.conocimientos
        ]
        return await self.list_conocimientos(referencia_id, competencia_id)

    async def delete_conocimiento(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        conocimiento_id: uuid.UUID,
    ) -> object:
        """Delete a SABER knowledge item in memory."""
        if competencia_id != self.competencia_id:
            raise ConocimientoSaberCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        if not any(item.id == conocimiento_id for item in self.conocimientos):
            raise ConocimientoSaberNotFoundError(
                "No existe el conocimiento SABER solicitado para esta competencia"
            )
        self.conocimientos = [
            item for item in self.conocimientos if item.id != conocimiento_id
        ]
        return {
            "referencia_id": referencia_id,
            "competencia_id": competencia_id,
            "conocimiento_id": conocimiento_id,
            "eliminado": True,
        }


def test_conocimientos_saber_endpoints_create_list_update_delete() -> None:
    """The HTTP API should expose the SABER knowledge CRUD contract."""
    fake_service = FakeProgramaConocimientoSaberService()
    app.dependency_overrides[get_programa_conocimiento_saber_service] = lambda: (
        fake_service
    )
    client = TestClient(app)
    referencia_id = uuid.uuid4()
    competencia_id = fake_service.competencia_id

    create_response = client.post(
        (
            f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
            "/conocimientos/saber"
        ),
        json={"descripcion": " Arquitectura de software "},
    )
    conocimiento_id = create_response.json()["conocimientos"][0]["id"]
    list_response = client.get(
        (
            f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
            "/conocimientos/saber"
        )
    )
    update_response = client.put(
        (
            f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
            f"/conocimientos/saber/{conocimiento_id}"
        ),
        json={"descripcion": "Patrones de arquitectura"},
    )
    delete_response = client.delete(
        (
            f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
            f"/conocimientos/saber/{conocimiento_id}"
        )
    )

    app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["referencia_id"] == str(referencia_id)
    assert create_response.json()["competencia_id"] == str(competencia_id)
    assert create_response.json()["conocimientos"][0]["tipo"] == "SABER"
    assert create_response.json()["conocimientos"][0]["descripcion"] == (
        "Arquitectura de software"
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["conocimientos"]) == 1
    assert update_response.status_code == 200
    assert update_response.json()["conocimientos"][0]["descripcion"] == (
        "Patrones de arquitectura"
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["eliminado"] is True


def test_conocimientos_saber_endpoint_rejects_duplicate_description() -> None:
    """The HTTP API should map duplicate SABER descriptions to conflict responses."""
    fake_service = FakeProgramaConocimientoSaberService()
    app.dependency_overrides[get_programa_conocimiento_saber_service] = lambda: (
        fake_service
    )
    client = TestClient(app)
    referencia_id = uuid.uuid4()
    competencia_id = fake_service.competencia_id

    client.post(
        (
            f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
            "/conocimientos/saber"
        ),
        json={"descripcion": "Arquitectura"},
    )
    response = client.post(
        (
            f"/api/v1/programas/{referencia_id}/competencias/{competencia_id}"
            "/conocimientos/saber"
        ),
        json={"descripcion": "Arquitectura"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ya existe un conocimiento SABER con esta descripcion exacta en la competencia"
    )


def test_conocimientos_saber_endpoint_rejects_blank_description() -> None:
    """The HTTP API should reject blank SABER descriptions."""
    fake_service = FakeProgramaConocimientoSaberService()
    app.dependency_overrides[get_programa_conocimiento_saber_service] = lambda: (
        fake_service
    )
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.post(
        (
            f"/api/v1/programas/{referencia_id}/competencias/"
            f"{fake_service.competencia_id}/conocimientos/saber"
        ),
        json={"descripcion": "   "},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_conocimientos_saber_endpoint_rejects_foreign_competencia() -> None:
    """The HTTP API should reject operations outside the current program."""
    fake_service = FakeProgramaConocimientoSaberService()
    app.dependency_overrides[get_programa_conocimiento_saber_service] = lambda: (
        fake_service
    )
    client = TestClient(app)
    referencia_id = uuid.uuid4()
    foreign_competencia_id = uuid.uuid4()

    response = client.get(
        (
            f"/api/v1/programas/{referencia_id}/competencias/"
            f"{foreign_competencia_id}/conocimientos/saber"
        )
    )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "La competencia no existe o no pertenece al programa actual"
    )


def test_conocimientos_saber_endpoint_rejects_explicit_proceso_type() -> None:
    """The TASK-10 endpoint should not accept PROCESO input."""
    fake_service = FakeProgramaConocimientoSaberService()
    app.dependency_overrides[get_programa_conocimiento_saber_service] = lambda: (
        fake_service
    )
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.post(
        (
            f"/api/v1/programas/{referencia_id}/competencias/"
            f"{fake_service.competencia_id}/conocimientos/saber"
        ),
        json={"descripcion": "Arquitectura", "tipo": "PROCESO"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422
