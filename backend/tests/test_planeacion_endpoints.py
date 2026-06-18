"""HTTP tests for Pedagogical Planning endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.application.dto.planeacion import (
    PlaneacionContextoDTO,
    PlaneacionListDTO,
    PlaneacionResponseDTO,
    PlaneacionSaveDTO,
)
from src.interfaces.http.app import app
from src.interfaces.http.controllers.planeacion import get_planeacion_service


class FakePlaneacionPedagogicaService:
    """Mock service double for planning HTTP endpoints."""

    def __init__(self) -> None:
        """Set up mock state."""
        self.contexto_mock: PlaneacionContextoDTO | None = None
        self.planeaciones: dict[uuid.UUID, PlaneacionResponseDTO] = {}

    async def obtener_contexto(self, referencia_id: uuid.UUID) -> PlaneacionContextoDTO:
        """Simulate contextual fetch."""
        if self.contexto_mock is None:
            raise ValueError("No context mock configured")
        return self.contexto_mock

    async def listar_planeaciones(
        self, proyecto_id: uuid.UUID
    ) -> list[PlaneacionListDTO]:
        """Simulate listing for dashboard."""
        return [
            PlaneacionListDTO(
                id=p.id,
                proyecto_id=p.proyecto_id,
                competencia_id=p.competencia_id,
                resultado_id=p.resultado_id,
                resultado_descripcion=p.resultado_descripcion or "Resultado mock",
                codigo_competencia="220501046",
                nombre_competencia="Desarrollar software",
                estado=p.estado,
                fecha_actualizacion=datetime.now(UTC),
            )
            for p in self.planeaciones.values()
            if p.proyecto_id == proyecto_id
        ]

    async def obtener_detalle(
        self, planeacion_id: uuid.UUID
    ) -> PlaneacionResponseDTO | None:
        """Simulate single retrieval."""
        return self.planeaciones.get(planeacion_id)

    async def guardar_borrador(self, dto: PlaneacionSaveDTO) -> PlaneacionResponseDTO:
        """Simulate draft saving."""
        planning_id = uuid.uuid4()
        response = PlaneacionResponseDTO(
            id=planning_id,
            proyecto_id=dto.proyecto_id,
            competencia_id=dto.competencia_id,
            resultado_id=dto.resultado_id,
            resultado_descripcion="Resultado mock",
            fase_id=dto.fase_id,
            actividad_id=dto.actividad_id,
            estado="BORRADOR",
            datos_complementarios=dto.datos_complementarios,
            resultados_ids=dto.resultados_ids,
            conocimientos_ids=dto.conocimientos_ids,
            criterios_ids=dto.criterios_ids,
            version=1,
        )
        self.planeaciones[planning_id] = response
        return response

    async def confirmar_y_generar(
        self, planeacion_id: uuid.UUID
    ) -> PlaneacionResponseDTO:
        """Simulate confirmation."""
        if planeacion_id not in self.planeaciones:
            raise ValueError(f"No existe la planeacion {planeacion_id}")
        p = self.planeaciones[planeacion_id]
        p.estado = "COMPLETO"
        p.storage_key = "mock-key"
        p.file_name = "mock-file.json"
        p.content_type = "application/json"
        p.fecha_generacion = datetime.now(UTC)
        return p

    async def eliminar_planeacion(self, planeacion_id: uuid.UUID) -> None:
        """Simulate delete."""
        self.planeaciones.pop(planeacion_id, None)


def test_planeacion_endpoints_flow() -> None:
    # Arrange
    fake_service = FakePlaneacionPedagogicaService()
    app.dependency_overrides[get_planeacion_service] = lambda: fake_service
    client = TestClient(app)

    referencia_id = uuid.uuid4()
    proyecto_id = uuid.uuid4()
    competencia_id = uuid.uuid4()
    resultado_id = uuid.uuid4()

    fake_service.contexto_mock = PlaneacionContextoDTO(
        programa_id=uuid.uuid4(),
        codigo_programa="228118",
        nombre_programa="Analisis de software",
        proyecto_id=proyecto_id,
        codigo_proyecto="PR-01",
        nombre_proyecto="Proyecto formativo test",
        competencias=[],
        fases=[],
    )

    # 1. Test GET Contexto
    context_res = client.get(f"/api/v1/planeaciones/contexto/{referencia_id}")
    assert context_res.status_code == 200
    assert context_res.json()["codigo_programa"] == "228118"

    # 2. Test POST save draft
    save_payload = {
        "proyecto_id": str(proyecto_id),
        "competencia_id": str(competencia_id),
        "resultado_id": str(resultado_id),
        "resultados_ids": [str(resultado_id)],
        "conocimientos_ids": [],
        "criterios_ids": [],
        "datos_complementarios": {"horas": 40},
    }
    save_res = client.post("/api/v1/planeaciones", json=save_payload)
    assert save_res.status_code == 200
    planning_id = save_res.json()["id"]
    assert save_res.json()["estado"] == "BORRADOR"
    assert save_res.json()["resultado_id"] == str(resultado_id)

    # 3. Test GET list
    list_res = client.get(f"/api/v1/planeaciones/proyecto/{proyecto_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == planning_id

    # 4. Test POST confirm/complete
    confirm_res = client.post(f"/api/v1/planeaciones/{planning_id}/confirmar")
    assert confirm_res.status_code == 200
    assert confirm_res.json()["estado"] == "COMPLETO"
    assert confirm_res.json()["storage_key"] == "mock-key"

    # 5. Test DELETE
    delete_res = client.delete(f"/api/v1/planeaciones/{planning_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["message"] == "Planeación pedagógica eliminada con éxito."

    app.dependency_overrides.clear()
