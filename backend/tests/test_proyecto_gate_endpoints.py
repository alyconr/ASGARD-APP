"""HTTP tests for TASK-15 project availability gate."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from src.application.dto.proyecto_gate import ProyectoDisponibilidadDTO
from src.application.services.proyecto_gate import ProyectoBloqueadoError
from src.domain.shared.enums import EstadoBloque
from src.interfaces.http.app import app
from src.interfaces.http.controllers.proyecto_gate import get_proyecto_gate_service


class FakeProyectoGateService:
    """Simple service double for project gate endpoint tests."""

    def __init__(self, *, bloqueado: bool) -> None:
        """Store the desired availability outcome."""
        self.bloqueado = bloqueado
        self.programa_id = uuid.uuid4()

    async def consultar_disponibilidad(
        self,
        referencia_id: uuid.UUID,
    ) -> ProyectoDisponibilidadDTO:
        """Return a deterministic availability result."""
        return _availability(
            referencia_id,
            self.programa_id,
            bloqueado=self.bloqueado,
        )

    async def validar_acceso(
        self,
        referencia_id: uuid.UUID,
    ) -> ProyectoDisponibilidadDTO:
        """Allow or reject access based on the configured outcome."""
        result = await self.consultar_disponibilidad(referencia_id)
        if result.proyecto_bloqueado:
            raise ProyectoBloqueadoError(result)
        return result


def _availability(
    referencia_id: uuid.UUID,
    programa_id: uuid.UUID,
    *,
    bloqueado: bool,
) -> ProyectoDisponibilidadDTO:
    estado_programa = EstadoBloque.BORRADOR if bloqueado else EstadoBloque.COMPLETO
    return ProyectoDisponibilidadDTO(
        referencia_id=referencia_id,
        programa_id=programa_id,
        estado_programa=estado_programa,
        programa_completo=not bloqueado,
        proyecto_bloqueado=bloqueado,
        estado_proyecto=EstadoBloque.BLOQUEADO if bloqueado else EstadoBloque.BORRADOR,
        motivo="PROGRAMA_NO_COMPLETO" if bloqueado else None,
        mensaje=(
            (
                "El modulo proyecto esta bloqueado hasta que el programa "
                "quede cerrado como COMPLETO."
            )
            if bloqueado
            else (
                "El proyecto formativo esta habilitado porque el programa "
                "esta COMPLETO."
            )
        ),
        accion_sugerida=(
            "completar_y_cerrar_programa" if bloqueado else "iniciar_proyecto"
        ),
    )


def test_disponibilidad_endpoint_returns_blocked_message() -> None:
    """The availability endpoint should explain why the project is blocked."""
    fake_service = FakeProyectoGateService(bloqueado=True)
    app.dependency_overrides[get_proyecto_gate_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.get(
        f"/api/v1/programas/{referencia_id}/proyecto/disponibilidad",
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["programa_completo"] is False
    assert response.json()["proyecto_bloqueado"] is True
    assert response.json()["motivo"] == "PROGRAMA_NO_COMPLETO"
    assert "bloqueado" in response.json()["mensaje"]


def test_acceso_endpoint_rejects_blocked_project() -> None:
    """The backend guard endpoint should reject blocked project access."""
    fake_service = FakeProyectoGateService(bloqueado=True)
    app.dependency_overrides[get_proyecto_gate_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.post(f"/api/v1/programas/{referencia_id}/proyecto/acceso")

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"]["proyecto_bloqueado"] is True
    assert response.json()["detail"]["programa_completo"] is False


def test_acceso_endpoint_allows_complete_program() -> None:
    """The backend guard endpoint should allow access when the program is complete."""
    fake_service = FakeProyectoGateService(bloqueado=False)
    app.dependency_overrides[get_proyecto_gate_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.post(f"/api/v1/programas/{referencia_id}/proyecto/acceso")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["programa_completo"] is True
    assert response.json()["proyecto_bloqueado"] is False
    assert response.json()["estado_proyecto"] == "BORRADOR"
