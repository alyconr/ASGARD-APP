"""HTTP tests for Pedagogical Planning endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from src.application.dto.planeacion import (
    FormatoOficialEstadoDTO,
    FormatoOficialGeneradoDTO,
    PlaneacionContextoDTO,
    PlaneacionDocumentoConfigDTO,
    PlaneacionDocumentoConfigUpdateDTO,
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
        self.configs: dict[uuid.UUID, PlaneacionDocumentoConfigDTO] = {}

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
                fase_id=p.fase_id,
                actividad_id=p.actividad_id,
                nombre_fase="Analisis",
                descripcion_actividad="Estructurar propuesta tecnica",
                actividades_aprendizaje="Actividad de prueba",
                estado=p.estado,
                competencias_count=1,
                resultados_count=len(p.resultados_ids),
                resultados_especificos=1,
                resultados_transversales=0,
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
            fase_id=dto.fase_id,
            actividad_id=dto.actividad_id,
            estado="BORRADOR",
            datos_complementarios=dto.datos_complementarios,
            resultados_ids=dto.resultados_ids,
            conocimientos_ids=dto.conocimientos_ids,
            criterios_ids=dto.criterios_ids,
            competencias=[],
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
        p.file_name = "GPFI-F-134V05-planeacion.xlsx"
        p.content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        p.fecha_generacion = datetime.now(UTC)
        return p

    async def obtener_configuracion_documento(
        self,
        proyecto_id: uuid.UUID,
    ) -> PlaneacionDocumentoConfigDTO:
        return self.configs.get(
            proyecto_id,
            PlaneacionDocumentoConfigDTO(proyecto_id=proyecto_id),
        )

    async def guardar_configuracion_documento(
        self,
        proyecto_id: uuid.UUID,
        dto: PlaneacionDocumentoConfigUpdateDTO,
    ) -> PlaneacionDocumentoConfigDTO:
        config = PlaneacionDocumentoConfigDTO(
            proyecto_id=proyecto_id,
            **dto.model_dump(),
        )
        self.configs[proyecto_id] = config
        return config

    async def obtener_estado_formato_individual(
        self,
        planeacion_id: uuid.UUID,
    ) -> FormatoOficialEstadoDTO:
        planning = self.planeaciones[planeacion_id]
        return FormatoOficialEstadoDTO(
            listo=True,
            planeaciones_completas=int(planning.estado == "COMPLETO"),
            storage_key=planning.storage_key,
            file_name=planning.file_name,
        )

    async def obtener_estado_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
    ) -> FormatoOficialEstadoDTO:
        complete = [
            planning
            for planning in self.planeaciones.values()
            if planning.proyecto_id == proyecto_id
            and planning.estado == "COMPLETO"
        ]
        return FormatoOficialEstadoDTO(
            listo=bool(complete),
            planeaciones_completas=len(complete),
        )

    async def generar_formato_individual(
        self,
        planeacion_id: uuid.UUID,
    ) -> FormatoOficialGeneradoDTO:
        planning = self.planeaciones[planeacion_id]
        now = datetime.now(UTC)
        return FormatoOficialGeneradoDTO(
            storage_key=planning.storage_key or "mock-key",
            file_name=planning.file_name or "GPFI-F-134V05-planeacion.xlsx",
            content_type=planning.content_type or "application/octet-stream",
            checksum_sha256="a" * 64,
            fecha_generacion=now,
            version=1,
            filas_generadas=1,
            planeaciones_incluidas=1,
        )

    async def generar_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
    ) -> FormatoOficialGeneradoDTO:
        complete = await self.obtener_estado_formato_consolidado(proyecto_id)
        return FormatoOficialGeneradoDTO(
            storage_key="consolidado/mock.xlsx",
            file_name="GPFI-F-134V05-planeacion-pedagogica.xlsx",
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            checksum_sha256="b" * 64,
            fecha_generacion=datetime.now(UTC),
            version=1,
            filas_generadas=complete.planeaciones_completas,
            planeaciones_incluidas=complete.planeaciones_completas,
        )

    async def descargar_formato_individual(
        self,
        planeacion_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        return b"PK\x03\x04mock", "GPFI-F-134V05-planeacion.xlsx"

    async def descargar_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        return b"PK\x03\x04mock", "GPFI-F-134V05-planeacion-pedagogica.xlsx"

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
    fase_id = uuid.uuid4()
    actividad_id = uuid.uuid4()
    resultado_id = uuid.uuid4()

    fake_service.contexto_mock = PlaneacionContextoDTO(
        programa_id=uuid.uuid4(),
        codigo_programa="228118",
        nombre_programa="Analisis de software",
        proyecto_id=proyecto_id,
        codigo_proyecto="PR-01",
        nombre_proyecto="Proyecto formativo test",
        fases=[],
    )

    # 1. Test GET Contexto
    context_res = client.get(f"/api/v1/planeaciones/contexto/{referencia_id}")
    assert context_res.status_code == 200
    assert context_res.json()["codigo_programa"] == "228118"

    # 2. Test POST save draft
    save_payload = {
        "proyecto_id": str(proyecto_id),
        "fase_id": str(fase_id),
        "actividad_id": str(actividad_id),
        "resultados_ids": [str(resultado_id)],
        "conocimientos_ids": [],
        "criterios_ids": [],
        "datos_complementarios": {"horas": 40},
    }
    save_res = client.post("/api/v1/planeaciones", json=save_payload)
    assert save_res.status_code == 200
    planning_id = save_res.json()["id"]
    assert save_res.json()["estado"] == "BORRADOR"
    assert save_res.json()["resultados_ids"] == [str(resultado_id)]

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

    # 5. Test official configuration
    config_payload = {
        "fecha_elaboracion": date.today().isoformat(),
        "modalidad_formacion": "Presencial",
        "clasificacion_informacion": "PUBLICA",
        "equipo_gestion_curricular": ["Ana Instructor"],
        "regional": "Distrito Capital",
        "centro_formacion": "Centro de prueba",
    }
    config_res = client.put(
        f"/api/v1/planeaciones/proyecto/{proyecto_id}/"
        "configuracion-formato-oficial",
        json=config_payload,
    )
    assert config_res.status_code == 200
    assert config_res.json()["modalidad_formacion"] == "Presencial"

    # 6. Test individual and consolidated real-download contracts
    individual_download = client.get(
        f"/api/v1/planeaciones/{planning_id}/descargar-formato-oficial"
    )
    assert individual_download.status_code == 200
    assert individual_download.content.startswith(b"PK")
    assert "spreadsheetml.sheet" in individual_download.headers["content-type"]

    consolidated_generate = client.post(
        f"/api/v1/planeaciones/proyecto/{proyecto_id}/generar-formato-oficial"
    )
    assert consolidated_generate.status_code == 200
    assert consolidated_generate.json()["planeaciones_incluidas"] == 1

    # 7. Test DELETE
    delete_res = client.delete(f"/api/v1/planeaciones/{planning_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["message"] == "Planeación pedagógica eliminada con éxito."

    app.dependency_overrides.clear()

