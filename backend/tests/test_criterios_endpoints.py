"""HTTP tests for TASK-12 criteria CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.application.dto.criterios import (
    CriterioDTO,
    CriterioListDTO,
    CriterioPayloadDTO,
)
from src.application.services.criterios import (
    CriterioCompetenciaNotFoundError,
    CriterioDuplicateError,
    CriterioNotFoundError,
)
from src.domain.shared.enums import EstadoCampo
from src.interfaces.http.app import app
from src.interfaces.http.controllers.criterios import (
    get_programa_criterios_service,
)


class FakeProgramaCriteriosService:
    def __init__(self) -> None:
        self.competencia_id = uuid.uuid4()
        self.criterios: list[CriterioDTO] = []

    async def list_criterios(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> CriterioListDTO:
        if competencia_id != self.competencia_id:
            raise CriterioCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        return CriterioListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia_id,
            criterios=self.criterios,
        )

    async def create_criterio(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        payload: CriterioPayloadDTO,
    ) -> CriterioListDTO:
        if competencia_id != self.competencia_id:
            raise CriterioCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        if payload.descripcion.strip() == "":
            raise ValueError("descripcion vacia")
        dto = CriterioDTO(
            id=uuid.uuid4(),
            competencia_id=competencia_id,
            resultado_id=None,
            descripcion=payload.descripcion.strip(),
            orden=len(self.criterios) + 1,
            estado=EstadoCampo.MANUAL,
            fecha_creacion=datetime.now(UTC),
            fecha_actualizacion=datetime.now(UTC),
        )
        self.criterios.append(dto)
        return CriterioListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia_id,
            criterios=self.criterios,
        )

    async def update_criterio(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        criterio_id: uuid.UUID,
        payload: CriterioPayloadDTO,
    ) -> CriterioListDTO:
        if competencia_id != self.competencia_id:
            raise CriterioCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        for c in self.criterios:
            if c.id == criterio_id:
                self.criterios = [
                    CriterioDTO(
                        id=c.id,
                        competencia_id=c.competencia_id,
                        resultado_id=c.resultado_id,
                        descripcion=payload.descripcion.strip(),
                        orden=c.orden,
                        estado=c.estado,
                        fecha_creacion=c.fecha_creacion,
                        fecha_actualizacion=datetime.now(UTC),
                    )
                    if item.id == criterio_id
                    else item
                    for item in self.criterios
                ]
                return CriterioListDTO(
                    referencia_id=referencia_id,
                    competencia_id=competencia_id,
                    criterios=self.criterios,
                )
        raise CriterioNotFoundError(
            "No existe el criterio de evaluacion solicitado para esta competencia"
        )

    async def delete_criterio(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        criterio_id: uuid.UUID,
    ):
        if competencia_id != self.competencia_id:
            raise CriterioCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        for c in self.criterios:
            if c.id == criterio_id:
                self.criterios = [
                    item for item in self.criterios if item.id != criterio_id
                ]
                return type(
                    "DeleteDTO",
                    (),
                    {
                        "referencia_id": referencia_id,
                        "competencia_id": competencia_id,
                        "criterio_id": criterio_id,
                        "eliminado": True,
                    },
                )()
        raise CriterioNotFoundError(
            "No existe el criterio de evaluacion solicitado para esta competencia"
        )


def _make_client(service_double):
    client = TestClient(app)
    app.dependency_overrides[get_programa_criterios_service] = lambda: service_double
    return client


class TestCreateCriterioEndpoint:
    def test_returns_201_and_list(self):
        fake = FakeProgramaCriteriosService()
        client = _make_client(fake)
        ref_id = uuid.uuid4()

        response = client.post(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios",
            json={"descripcion": "  Analiza requerimientos  "},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["referencia_id"] == str(ref_id)
        assert len(data["criterios"]) == 1
        assert data["criterios"][0]["descripcion"] == "Analiza requerimientos"

    def test_rejects_empty_description(self):
        fake = FakeProgramaCriteriosService()
        client = _make_client(fake)
        ref_id = uuid.uuid4()

        response = client.post(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios",
            json={"descripcion": "   "},
        )

        assert response.status_code == 422

    def test_rejects_missing_description(self):
        fake = FakeProgramaCriteriosService()
        client = _make_client(fake)
        ref_id = uuid.uuid4()

        response = client.post(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios",
            json={},
        )

        assert response.status_code == 422


class TestListCriteriosEndpoint:
    def test_returns_200_and_empty_list(self):
        fake = FakeProgramaCriteriosService()
        client = _make_client(fake)
        ref_id = uuid.uuid4()

        response = client.get(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["criterios"] == []


class TestUpdateCriterioEndpoint:
    def test_updates_and_returns_list(self):
        fake = FakeProgramaCriteriosService()
        client = _make_client(fake)
        ref_id = uuid.uuid4()
        create_response = client.post(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios",
            json={"descripcion": "Original"},
        )
        criterio_id = create_response.json()["criterios"][0]["id"]

        response = client.put(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios/{criterio_id}",
            json={"descripcion": "Actualizado"},
        )

        assert response.status_code == 200
        assert response.json()["criterios"][0]["descripcion"] == "Actualizado"


class TestDeleteCriterioEndpoint:
    def test_deletes_and_returns_confirmation(self):
        fake = FakeProgramaCriteriosService()
        client = _make_client(fake)
        ref_id = uuid.uuid4()
        create_response = client.post(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios",
            json={"descripcion": "Para eliminar"},
        )
        criterio_id = create_response.json()["criterios"][0]["id"]

        response = client.delete(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios/{criterio_id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["eliminado"] is True
        assert data["criterio_id"] == criterio_id

    def test_rejects_delete_of_missing_criterio(self):
        fake = FakeProgramaCriteriosService()
        client = _make_client(fake)
        ref_id = uuid.uuid4()

        response = client.delete(
            f"/api/v1/programas/{ref_id}/competencias/{fake.competencia_id}/criterios/{uuid.uuid4()}",
        )

        assert response.status_code == 404
