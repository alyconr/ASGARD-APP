"""Tests for the integrated PlaneacionPedagogicaService."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dto.planeacion import PlaneacionSaveDTO
from src.application.services.planeacion_formato_excel import (
    EXCEL_CONTENT_TYPE,
    FormatoExcelResultado,
    PlaneacionFormatoExcelService,
)
from src.application.services.planeacion_service import (
    PlaneacionAccessError,
    PlaneacionPedagogicaService,
)
from src.domain.shared.enums import EstadoBloque, TipoConocimiento
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
)
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    AsignacionCurricularProyecto,
    FaseProyecto,
    ProyectoFormativo,
)
from src.infrastructure.repositories.planeacion import PlaneacionPedagogicaRepository

pytestmark = pytest.mark.anyio


class FakePlaneacionSession:
    """In-memory session that routes queries by mapped entity type."""

    def __init__(self) -> None:
        self.objects: dict[uuid.UUID, Any] = {}
        self.registry: dict[type, list[Any]] = {}
        self.added: list[Any] = []

    def register(self, instance: Any) -> Any:
        self.objects[instance.id] = instance
        self.registry.setdefault(type(instance), []).append(instance)
        return instance

    async def get(self, entity_type: type, object_id: uuid.UUID, options=None):
        return self.objects.get(object_id)

    @staticmethod
    def _extract_in_ids(statement) -> list[Any] | None:
        try:
            for criterion in statement._where_criteria:
                right = getattr(criterion, "right", None)
                if right is None:
                    continue
                for attribute in ("effective_value", "value"):
                    value = getattr(right, attribute, None)
                    if isinstance(value, (list, tuple, set)):
                        return list(value)
        except Exception:
            return None
        return None

    async def execute(self, statement):
        entity = None
        try:
            entity = statement.column_descriptions[0].get("entity")
        except Exception:
            entity = None
        items = self.registry.get(entity, [])
        in_ids = self._extract_in_ids(statement)
        if in_ids is not None:
            wanted = {value for value in in_ids}
            items = [item for item in items if getattr(item, "id", None) in wanted]
        result = MagicMock()
        scalars = MagicMock()
        scalars.unique.return_value.all.return_value = items
        scalars.all.return_value = items
        result.scalars.return_value = scalars
        result.scalar_one_or_none.return_value = items[0] if items else None
        return result

    def add(self, instance: Any) -> None:
        if instance.id is None:
            instance.id = uuid.uuid4()
        self.added.append(instance)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass


def _build_base_context() -> dict[str, Any]:
    """Build a complete program/project/assignment fixture set."""
    programa_id = uuid.uuid4()
    programa = ProgramaFormacion(
        codigo_programa="228118",
        nombre_programa="Analisis de software",
        version_programa="1",
        modalidad_formacion="Presencial",
        estado=EstadoBloque.COMPLETO,
    )
    programa.id = programa_id

    comp_tecnica = Competencia(
        codigo_competencia="220501094",
        nombre_competencia="Estructurar propuesta tecnica",
    )
    comp_tecnica.id = uuid.uuid4()
    comp_tecnica.orden = 1
    comp_tecnica.programa_id = programa_id
    rap_t1 = ResultadoAprendizaje(
        codigo_resultado="220501094-RAP01",
        descripcion="Definir especificaciones tecnicas",
    )
    rap_t1.id = uuid.uuid4()
    rap_t1.competencia_id = comp_tecnica.id
    rap_t2 = ResultadoAprendizaje(
        codigo_resultado="220501094-RAP03",
        descripcion="Validar condiciones",
    )
    rap_t2.id = uuid.uuid4()
    rap_t2.competencia_id = comp_tecnica.id
    comp_tecnica.resultados = [rap_t1, rap_t2]

    saber_t = Conocimiento(
        tipo=TipoConocimiento.SABER, descripcion="Saber tecnico"
    )
    saber_t.id = uuid.uuid4()
    saber_t.competencia_id = comp_tecnica.id
    proceso_t = Conocimiento(
        tipo=TipoConocimiento.PROCESO, descripcion="Proceso tecnico"
    )
    proceso_t.id = uuid.uuid4()
    proceso_t.competencia_id = comp_tecnica.id
    criterio_t = CriterioEvaluacion(descripcion="Criterio tecnico")
    criterio_t.id = uuid.uuid4()
    criterio_t.competencia_id = comp_tecnica.id
    comp_tecnica.conocimientos = [saber_t, proceso_t]
    comp_tecnica.criterios = [criterio_t]

    comp_trans = Competencia(
        codigo_competencia="240201524",
        nombre_competencia="Comunicacion efectiva",
    )
    comp_trans.id = uuid.uuid4()
    comp_trans.orden = 2
    comp_trans.programa_id = programa_id
    rap_x1 = ResultadoAprendizaje(
        codigo_resultado="240201524-RAP03",
        descripcion="Relacionar procesos comunicativos",
    )
    rap_x1.id = uuid.uuid4()
    rap_x1.competencia_id = comp_trans.id
    comp_trans.resultados = [rap_x1]

    saber_x = Conocimiento(
        tipo=TipoConocimiento.SABER, descripcion="Saber comunicacion"
    )
    saber_x.id = uuid.uuid4()
    saber_x.competencia_id = comp_trans.id
    criterio_x = CriterioEvaluacion(descripcion="Criterio comunicacion")
    criterio_x.id = uuid.uuid4()
    criterio_x.competencia_id = comp_trans.id
    comp_trans.conocimientos = [saber_x]
    comp_trans.criterios = [criterio_x]

    programa.competencias = [comp_tecnica, comp_trans]

    proyecto = ProyectoFormativo(
        codigo_proyecto="PR-001",
        nombre_proyecto="Proyecto integrado",
        version_proyecto="1",
        estado=EstadoBloque.COMPLETO,
    )
    proyecto.id = uuid.uuid4()
    proyecto.programa_id = programa_id
    proyecto.programa = programa

    fase = FaseProyecto(nombre_fase="Analisis")
    fase.id = uuid.uuid4()
    fase.proyecto_id = proyecto.id
    fase.orden = 1

    actividad = ActividadProyecto(descripcion="Estructurar la propuesta")
    actividad.id = uuid.uuid4()
    actividad.fase_id = fase.id
    actividad.orden = 1
    fase.actividades = [actividad]
    proyecto.fases = [fase]

    asignaciones = [
        AsignacionCurricularProyecto(
            proyecto_id=proyecto.id,
            actividad_proyecto_id=actividad.id,
            competencia_id=comp_tecnica.id,
            resultado_id=rap_t1.id,
            tipo_resultado="ESPECIFICO",
            orden_resultado=1,
        ),
        AsignacionCurricularProyecto(
            proyecto_id=proyecto.id,
            actividad_proyecto_id=actividad.id,
            competencia_id=comp_tecnica.id,
            resultado_id=rap_t2.id,
            tipo_resultado="ESPECIFICO",
            orden_resultado=3,
        ),
        AsignacionCurricularProyecto(
            proyecto_id=proyecto.id,
            actividad_proyecto_id=actividad.id,
            competencia_id=comp_trans.id,
            resultado_id=rap_x1.id,
            tipo_resultado="TRANSVERSAL",
            orden_resultado=1,
        ),
    ]
    for asignacion, competencia, resultado in zip(
        asignaciones, [comp_tecnica, comp_tecnica, comp_trans], [rap_t1, rap_t2, rap_x1]
    ):
        asignacion.id = uuid.uuid4()
        asignacion.competencia = competencia
        asignacion.resultado = resultado

    return {
        "programa": programa,
        "proyecto": proyecto,
        "fase": fase,
        "actividad": actividad,
        "comp_tecnica": comp_tecnica,
        "comp_trans": comp_trans,
        "rap_t1": rap_t1,
        "rap_t2": rap_t2,
        "rap_x1": rap_x1,
        "saber_t": saber_t,
        "proceso_t": proceso_t,
        "criterio_t": criterio_t,
        "saber_x": saber_x,
        "criterio_x": criterio_x,
        "asignaciones": asignaciones,
    }


def _build_context_session(fx: dict[str, Any]) -> FakePlaneacionSession:
    session = FakePlaneacionSession()
    session.register(fx["programa"])
    session.register(fx["proyecto"])
    session.register(fx["fase"])
    session.register(fx["actividad"])
    session.register(fx["comp_tecnica"])
    session.register(fx["comp_trans"])
    session.register(fx["rap_t1"])
    session.register(fx["rap_t2"])
    session.register(fx["rap_x1"])
    session.register(fx["saber_t"])
    session.register(fx["proceso_t"])
    session.register(fx["criterio_t"])
    session.register(fx["saber_x"])
    session.register(fx["criterio_x"])
    for asignacion in fx["asignaciones"]:
        session.register(asignacion)
    return session


def _build_service(
    session: FakePlaneacionSession,
    repository: Any,
    formato_excel_service: Any = None,
) -> PlaneacionPedagogicaService:
    return PlaneacionPedagogicaService(
        session=session,
        repository=repository,
        storage_service=AsyncMock(),
        formato_excel_service=formato_excel_service,
    )


class TestObtenerContexto:
    async def test_contexto_returns_nested_phase_activity_competency_tree(self):
        fx = _build_base_context()
        session = _build_context_session(fx)

        referencia_id = uuid.uuid4()
        draft = MagicMock()
        draft.payload_json = {
            "curricular": {"programa_formacion_id": str(fx["programa"].id)}
        }
        draft_result = MagicMock()
        draft_result.scalar_one_or_none.return_value = draft

        original_execute = session.execute

        async def execute_with_draft(statement):
            entity = None
            try:
                entity = statement.column_descriptions[0].get("entity")
            except Exception:
                entity = None
            from src.infrastructure.db.models.drafts import BorradorSesion

            if entity is BorradorSesion or entity is None:
                return draft_result
            return await original_execute(statement)

        session.execute = execute_with_draft

        service = _build_service(session, MagicMock())
        contexto = await service.obtener_contexto(referencia_id)

        assert contexto.programa_id == fx["programa"].id
        assert contexto.proyecto_id == fx["proyecto"].id
        assert len(contexto.fases) == 1
        fase = contexto.fases[0]
        assert fase.nombre_fase == "Analisis"
        assert len(fase.actividades) == 1
        actividad = fase.actividades[0]
        assert actividad.descripcion == "Estructurar la propuesta"
        assert len(actividad.competencias) == 2

    async def test_contexto_shows_only_activity_assigned_competencies(self):
        fx = _build_base_context()
        session = _build_context_session(fx)

        # A second activity with no assignments must show no competencies.
        actividad_vacia = ActividadProyecto(descripcion="Actividad sin asignacion")
        actividad_vacia.id = uuid.uuid4()
        actividad_vacia.fase_id = fx["fase"].id
        actividad_vacia.orden = 2
        fx["fase"].actividades.append(actividad_vacia)
        session.register(actividad_vacia)

        draft = MagicMock()
        draft.payload_json = {
            "curricular": {"programa_formacion_id": str(fx["programa"].id)}
        }
        draft_result = MagicMock()
        draft_result.scalar_one_or_none.return_value = draft
        original_execute = session.execute

        async def execute_with_draft(statement):
            entity = None
            try:
                entity = statement.column_descriptions[0].get("entity")
            except Exception:
                entity = None
            from src.infrastructure.db.models.drafts import BorradorSesion

            if entity is BorradorSesion or entity is None:
                return draft_result
            return await original_execute(statement)

        session.execute = execute_with_draft
        service = _build_service(session, MagicMock())
        contexto = await service.obtener_contexto(uuid.uuid4())

        actividades = contexto.fases[0].actividades
        by_desc = {a.descripcion: a for a in actividades}
        assert len(by_desc["Estructurar la propuesta"].competencias) == 2
        assert by_desc["Actividad sin asignacion"].competencias == []

    async def test_contexto_resultados_carry_tipo_resultado(self):
        fx = _build_base_context()
        session = _build_context_session(fx)
        draft = MagicMock()
        draft.payload_json = {
            "curricular": {"programa_formacion_id": str(fx["programa"].id)}
        }
        draft_result = MagicMock()
        draft_result.scalar_one_or_none.return_value = draft
        original_execute = session.execute

        async def execute_with_draft(statement):
            entity = None
            try:
                entity = statement.column_descriptions[0].get("entity")
            except Exception:
                entity = None
            from src.infrastructure.db.models.drafts import BorradorSesion

            if entity is BorradorSesion or entity is None:
                return draft_result
            return await original_execute(statement)

        session.execute = execute_with_draft
        service = _build_service(session, MagicMock())
        contexto = await service.obtener_contexto(uuid.uuid4())

        actividad = contexto.fases[0].actividades[0]
        tipos: dict[str, list[str]] = {}
        for competencia in actividad.competencias:
            tipos[competencia.codigo_competencia] = [
                resultado.tipo_resultado for resultado in competencia.resultados
            ]
        assert tipos["220501094"] == ["ESPECIFICO", "ESPECIFICO"]
        assert tipos["240201524"] == ["TRANSVERSAL"]

    async def test_contexto_rejects_project_not_complete(self):
        fx = _build_base_context()
        fx["proyecto"].estado = EstadoBloque.BORRADOR
        session = _build_context_session(fx)
        draft = MagicMock()
        draft.payload_json = {
            "curricular": {"programa_formacion_id": str(fx["programa"].id)}
        }
        draft_result = MagicMock()
        draft_result.scalar_one_or_none.return_value = draft
        original_execute = session.execute

        async def execute_with_draft(statement):
            entity = None
            try:
                entity = statement.column_descriptions[0].get("entity")
            except Exception:
                entity = None
            from src.infrastructure.db.models.drafts import BorradorSesion

            if entity is BorradorSesion or entity is None:
                return draft_result
            return await original_execute(statement)

        session.execute = execute_with_draft
        service = _build_service(session, MagicMock())
        with pytest.raises(PlaneacionAccessError):
            await service.obtener_contexto(uuid.uuid4())


class TestGuardarBorrador:
    def _dto(self, fx: dict[str, Any], **overrides) -> PlaneacionSaveDTO:
        payload = {
            "proyecto_id": fx["proyecto"].id,
            "fase_id": fx["fase"].id,
            "actividad_id": fx["actividad"].id,
            "resultados_ids": [fx["rap_t1"].id, fx["rap_t2"].id, fx["rap_x1"].id],
            "conocimientos_ids": [fx["saber_t"].id, fx["saber_x"].id],
            "criterios_ids": [fx["criterio_t"].id, fx["criterio_x"].id],
            "datos_complementarios": {
                "actividades_aprendizaje": "Analizar y estructurar"
            },
        }
        payload.update(overrides)
        return PlaneacionSaveDTO(**payload)

    async def test_guardar_multicompetencia_persists_single_planning(self):
        fx = _build_base_context()
        session = _build_context_session(fx)
        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        repository.get_by_proyecto_and_actividad.return_value = None

        created = PlaneacionPedagogica(
            proyecto_id=fx["proyecto"].id,
            fase_id=fx["fase"].id,
            actividad_id=fx["actividad"].id,
        )
        created.id = uuid.uuid4()
        created.estado = EstadoBloque.BORRADOR
        created.datos_complementarios = {
            "actividades_aprendizaje": "Analizar y estructurar"
        }
        created.resultados = [fx["rap_t1"], fx["rap_t2"], fx["rap_x1"]]
        created.conocimientos = [fx["saber_t"], fx["saber_x"]]
        created.criterios = [fx["criterio_t"], fx["criterio_x"]]
        created.version = 1
        repository.get_by_id.return_value = created

        service = _build_service(session, repository)
        response = await service.guardar_borrador(self._dto(fx))

        repository.save.assert_called_once()
        saved = repository.save.call_args[0][0]
        assert saved.proyecto_id == fx["proyecto"].id
        assert saved.actividad_id == fx["actividad"].id
        assert len(saved.resultados) == 3
        assert len(response.resultados_ids) == 3

    async def test_guardar_rechaza_rap_no_asignado_a_actividad(self):
        fx = _build_base_context()
        session = _build_context_session(fx)
        # Register an extra RAP that is NOT assigned to the activity.
        rap_ajeno = ResultadoAprendizaje(
            codigo_resultado="AJENO", descripcion="Resultado ajeno"
        )
        rap_ajeno.id = uuid.uuid4()
        rap_ajeno.competencia_id = fx["comp_tecnica"].id
        session.register(rap_ajeno)

        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        service = _build_service(session, repository)
        dto = self._dto(fx, resultados_ids=[fx["rap_t1"].id, rap_ajeno.id])
        with pytest.raises(ValueError, match="no esta asociado"):
            await service.guardar_borrador(dto)
        repository.save.assert_not_called()

    async def test_guardar_rechaza_saber_de_competencia_no_seleccionada(self):
        fx = _build_base_context()
        # Remove transversal RAP so only the technical competency is selected.
        session = _build_context_session(fx)
        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        service = _build_service(session, repository)
        dto = self._dto(
            fx,
            resultados_ids=[fx["rap_t1"].id],
            conocimientos_ids=[fx["saber_t"].id, fx["saber_x"].id],
        )
        with pytest.raises(ValueError, match="saberes"):
            await service.guardar_borrador(dto)
        repository.save.assert_not_called()

    async def test_guardar_rechaza_criterio_incompatible(self):
        fx = _build_base_context()
        session = _build_context_session(fx)
        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        service = _build_service(session, repository)
        dto = self._dto(
            fx,
            resultados_ids=[fx["rap_t1"].id],
            conocimientos_ids=[fx["saber_t"].id],
            criterios_ids=[fx["criterio_t"].id, fx["criterio_x"].id],
        )
        with pytest.raises(ValueError, match="criterios"):
            await service.guardar_borrador(dto)
        repository.save.assert_not_called()

    async def test_guardar_rechaza_actividad_de_otra_fase(self):
        fx = _build_base_context()
        session = _build_context_session(fx)
        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        service = _build_service(session, repository)
        otra_fase = FaseProyecto(nombre_fase="Otra fase")
        otra_fase.id = uuid.uuid4()
        otra_fase.proyecto_id = fx["proyecto"].id
        session.register(otra_fase)
        dto = self._dto(fx, fase_id=otra_fase.id)
        with pytest.raises(ValueError, match="no pertenece a la fase"):
            await service.guardar_borrador(dto)
        repository.save.assert_not_called()

    async def test_guardar_rechaza_proyecto_no_completo(self):
        fx = _build_base_context()
        fx["proyecto"].estado = EstadoBloque.BORRADOR
        session = _build_context_session(fx)
        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        service = _build_service(session, repository)
        with pytest.raises(PlaneacionAccessError):
            await service.guardar_borrador(self._dto(fx))
        repository.save.assert_not_called()


class TestConfirmarYBrechas:
    async def test_confirmar_generates_single_workbook_for_multi_rap(self):
        fx = _build_base_context()
        session = _build_context_session(fx)

        planning = PlaneacionPedagogica(
            proyecto_id=fx["proyecto"].id,
            fase_id=fx["fase"].id,
            actividad_id=fx["actividad"].id,
            datos_complementarios={
                "actividades_aprendizaje": "Actividad integrada",
                "duracion_actividad_horas": 20,
                "horas_trabajo_directo": 12,
                "horas_trabajo_independiente": 8,
                "descripcion_evidencia_aprendizaje": "Evidencia",
                "estrategias_didacticas": "ABP",
                "ambiente": "Aula",
                "materiales_formacion": "Computador",
                "instructores": "Ana",
            },
        )
        planning.id = uuid.uuid4()
        planning.estado = EstadoBloque.BORRADOR
        planning.proyecto = fx["proyecto"]
        planning.fase = fx["fase"]
        planning.actividad = fx["actividad"]
        planning.resultados = [fx["rap_t1"], fx["rap_t2"], fx["rap_x1"]]
        planning.conocimientos = [fx["saber_t"], fx["proceso_t"], fx["saber_x"]]
        planning.criterios = [fx["criterio_t"], fx["criterio_x"]]
        planning.version = 1

        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        repository.get_by_id.return_value = planning
        repository.get_document_config.return_value = PlaneacionDocumentoConfig(
            proyecto_id=fx["proyecto"].id,
            fecha_elaboracion=date(2026, 8, 1),
            clasificacion_informacion="PUBLICA",
            equipo_gestion_curricular=["Ana"],
            regional="Distrito Capital",
            centro_formacion="Centro",
        )

        formato = MagicMock(spec=PlaneacionFormatoExcelService)
        formato.generar.return_value = FormatoExcelResultado(
            content=b"PK\x03\x04official",
            checksum_sha256="b" * 64,
            filas_generadas=3,
        )

        service = _build_service(session, repository, formato_excel_service=formato)
        response = await service.confirmar_y_generar(planning.id)

        assert response.estado == "COMPLETO"
        assert response.storage_key is not None
        assert "planeaciones-pedagogicas/" in response.storage_key
        # One row per selected RAP.
        rows = formato.generar.call_args[1]["rows"]
        assert len(rows) == 3

    async def test_hours_not_duplicated_across_rap_rows(self):
        fx = _build_base_context()
        session = _build_context_session(fx)

        planning = PlaneacionPedagogica(
            proyecto_id=fx["proyecto"].id,
            fase_id=fx["fase"].id,
            actividad_id=fx["actividad"].id,
            datos_complementarios={
                "actividades_aprendizaje": "Actividad integrada",
                "duracion_actividad_horas": 20,
                "horas_trabajo_directo": 12,
                "horas_trabajo_independiente": 8,
                "descripcion_evidencia_aprendizaje": "Evidencia",
                "estrategias_didacticas": "ABP",
                "ambiente": "Aula",
                "materiales_formacion": "Computador",
                "instructores": "Ana",
            },
        )
        planning.id = uuid.uuid4()
        planning.estado = EstadoBloque.COMPLETO
        planning.proyecto = fx["proyecto"]
        planning.fase = fx["fase"]
        planning.actividad = fx["actividad"]
        planning.resultados = [fx["rap_t1"], fx["rap_t2"], fx["rap_x1"]]
        planning.conocimientos = [fx["saber_t"], fx["proceso_t"], fx["saber_x"]]
        planning.criterios = [fx["criterio_t"], fx["criterio_x"]]
        planning.version = 1

        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        service = _build_service(session, repository)
        rows = await service._build_rows([planning])
        assert len(rows) == 3
        horas_directo = [r.horas_trabajo_directo for r in rows]
        horas_independiente = [r.horas_trabajo_independiente for r in rows]
        assert sum(v for v in horas_directo if v is not None) == 12
        assert sum(v for v in horas_independiente if v is not None) == 8
        assert [v is not None for v in horas_directo] == [True, False, False]


class TestLegacyCompatibility:
    async def test_detalle_de_planeacion_un_rap_histórica(self):
        """A historical single-RAP planning loads as integrated 1 comp/1 RAP."""
        fx = _build_base_context()
        session = _build_context_session(fx)

        planning = PlaneacionPedagogica(
            proyecto_id=fx["proyecto"].id,
            fase_id=fx["fase"].id,
            actividad_id=fx["actividad"].id,
            datos_complementarios={"actividades_aprendizaje": "Historica"},
        )
        planning.id = uuid.uuid4()
        planning.estado = EstadoBloque.COMPLETO
        planning.resultados = [fx["rap_t1"]]
        planning.conocimientos = []
        planning.criterios = []
        planning.version = 1

        repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
        repository.get_by_id.return_value = planning
        service = _build_service(session, repository)

        detail = await service.obtener_detalle(planning.id)
        assert detail is not None
        assert len(detail.resultados_ids) == 1
        assert len(detail.competencias) == 1
        assert detail.competencias[0].competencia_id == fx["comp_tecnica"].id
        assert len(detail.competencias[0].resultados) == 1
