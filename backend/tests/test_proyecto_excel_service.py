"""Tests for project Excel import service."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from openpyxl import Workbook

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.application.services.proyecto_excel import (
    InvalidProjectExcelUploadError,
    ProjectExcelDraftMissingError,
    ProjectExcelMissingPreviewError,
    ProyectoExcelImportService,
)
from src.domain.shared.enums import EstadoBloque

pytestmark = pytest.mark.anyio


class MockDraftRepository:
    def __init__(self, draft=None, program_draft=None):
        self.draft = draft
        self.program_draft = program_draft
        self.saved = False

    async def get_by_block_reference(self, tipo_bloque, referencia_id):
        if getattr(tipo_bloque, "value", tipo_bloque) == "PROGRAMA":
            return self.program_draft
        return self.draft

    async def save(self, draft):
        self.saved = True
        return draft


class MockAuditRepository:
    def __init__(self):
        self.events = []

    async def add_event(self, entidad, entidad_id, accion, detalle=None):
        self.events.append({"entidad": entidad, "accion": accion, "detalle": detalle})


class MockSession:
    def __init__(self):
        self.committed = False
        self.refreshed = False

    async def commit(self):
        self.committed = True

    async def refresh(self, instance):
        self.refreshed = True


class MockStorageService:
    def __init__(self, document=None, content=b""):
        self.document = document or StoredDocumentDTO(
            original_filename="proyecto.xlsx",
            storage_key="proyectos-formativos/test-id/excel/test.xlsx",
            size_bytes=1024,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            checksum_sha256="abc123",
            etag="etag-123",
        )
        self._content = content

    async def save_excel(self, *, key, content, content_type, original_filename):
        self._content = content
        return self.document

    async def read_excel(self, *, key):
        if not self._content:
            raise FileNotFoundError("Excel no encontrado")
        return self._content


class MockProjectRepository:
    def __init__(self):
        self.created_proyectos = []
        self.created_fases = []
        self.created_actividades = []
        self.created_programa_ids = []

    async def create_proyecto(
        self,
        *,
        programa_id,
        codigo_proyecto,
        nombre_proyecto,
        version_proyecto,
    ):
        p = MagicMock(id=uuid.uuid4())
        p.codigo_proyecto = codigo_proyecto
        self.created_programa_ids.append(programa_id)
        self.created_proyectos.append(p)
        return p

    async def create_fase(self, *, proyecto_id, nombre_fase, orden):
        f = MagicMock(id=uuid.uuid4())
        f.nombre_fase = nombre_fase
        self.created_fases.append(f)
        return f

    async def create_actividad(self, *, fase_id, descripcion, orden):
        a = MagicMock(id=uuid.uuid4())
        a.descripcion = descripcion
        self.created_actividades.append(a)
        return a

    async def proyecto_exists(self, *, programa_id):
        return False


def create_valid_workbook():
    wb = Workbook()

    proyecto_sheet = wb.active
    proyecto_sheet.title = "Proyecto"
    proyecto_sheet.append(
        [
            "proyecto_id",
            "nombre_proyecto",
            "codigo_proyecto_sofia",
            "codigo_programa",
            "nombre_programa",
            "fuente_archivo",
            "observaciones",
        ],
    )
    proyecto_sheet.append(
        [
            "PROJ-01",
            "Proyecto de prueba",
            "PR-001",
            "prog-ref",
            "Programa de prueba",
            "fuente.pdf",
            "observaciones proyecto",
        ]
    )

    planeacion_sheet = wb.create_sheet("Planeacion_Proyecto")
    planeacion_sheet.append(
        [
            "proyecto_id",
            "fase_id",
            "fase_proyecto",
            "actividad_id",
            "actividad_proyecto",
            "tipo_resultado",
            "competencia_id",
            "codigo_competencia",
            "nombre_competencia",
            "rap_id",
            "rap_numero",
            "resultado_aprendizaje",
            "orden_fase",
            "orden_actividad",
            "orden_resultado",
            "pagina_origen",
            "observaciones",
        ],
    )
    planeacion_sheet.append(
        [
            "PROJ-01",
            "F1",
            "Fase 1",
            "A1",
            "Actividad 1.1",
            "ESPECIFICO",
            "C1",
            "240201050",
            "Competencia de prueba 1",
            "R1",
            "1",
            "Resultado de aprendizaje 1",
            1,
            1,
            1,
            "12",
            "",
        ]
    )
    planeacion_sheet.append(
        [
            "PROJ-01",
            "F1",
            "Fase 1",
            "A2",
            "Actividad 1.2",
            "ESPECIFICO",
            "C1",
            "240201050",
            "Competencia de prueba 1",
            "R2",
            "2",
            "Resultado de aprendizaje 2",
            1,
            2,
            2,
            "13",
            "",
        ]
    )
    planeacion_sheet.append(
        [
            "PROJ-01",
            "F2",
            "Fase 2",
            "A3",
            "Actividad 2.1",
            "TRANSVERSAL",
            "C2",
            "240201051",
            "Competencia de prueba 2",
            "R3",
            "1",
            "Resultado de aprendizaje 3",
            2,
            1,
            1,
            "15",
            "",
        ]
    )

    validacion_sheet = wb.create_sheet("Validacion_Proyecto")
    validacion_sheet.append(
        [
            "tipo_validacion",
            "descripcion",
            "estado",
            "observaciones",
        ]
    )
    validacion_sheet.append(
        [
            "CURRICULAR",
            "Validacion basica del diseno",
            "OK",
            "Ninguna",
        ]
    )

    return wb


@pytest.fixture
def draft_factory():
    def _build():
        return MagicMock(
            id=uuid.uuid4(),
            payload_json={
                "meta": {
                    "referenciaId": str(uuid.uuid4()),
                    "programaId": "00000000-0000-0000-0000-000000000000",
                    "touchedSteps": ["fuente-proyecto"],
                    "lastInteractionAt": datetime.now(UTC).isoformat(),
                },
                "documental": {},
            },
            paso_actual="fuente-proyecto",
            estado_borrador=EstadoBloque.BORRADOR,
        )

    return _build


@pytest.fixture
def service(draft_factory):
    session = MockSession()
    draft_repository = MockDraftRepository(draft_factory())
    audit_repository = MockAuditRepository()
    storage_service = MockStorageService()
    project_repository = MockProjectRepository()

    return ProyectoExcelImportService(
        session=session,
        draft_repository=draft_repository,
        audit_repository=audit_repository,
        project_repository=project_repository,
        storage_service=storage_service,
    )


class TestPreviewProjectExcel:
    async def test_preview_accepts_valid_workbook(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        result = await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert result.valid is True
        assert result.estado_validacion == "VALIDO"
        assert result.proyecto is not None
        assert result.proyecto.codigo_proyecto == "PR-001"
        assert len(result.fases) == 2

    async def test_preview_rejects_missing_sheets(self, service):
        wb = Workbook()
        proyecto_sheet = wb.active
        proyecto_sheet.title = "Proyecto"
        proyecto_sheet.append(
            [
                "proyecto_id",
                "nombre_proyecto",
                "codigo_proyecto_sofia",
                "codigo_programa",
                "nombre_programa",
                "fuente_archivo",
                "observaciones",
            ]
        )
        proyecto_sheet.append(
            [
                "PROJ-01",
                "Proyecto de prueba",
                "PR-001",
                "prog-99",
                "Prog Name",
                "test.pdf",
                "",
            ]
        )
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        result = await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert result.valid is False
        assert result.estado_validacion == "INVALIDO"
        assert len(result.errores) > 0

    async def test_preview_rejects_non_xlsx(self, service):
        with pytest.raises(
            InvalidProjectExcelUploadError,
            match="Solo se aceptan archivos .xlsx",
        ):
            await service.preview_project_excel(
                referencia_id=uuid.uuid4(),
                filename="proyecto.pdf",
                content_type="application/pdf",
                content=b"fake pdf",
            )

    async def test_preview_rejects_empty_content(self, service):
        with pytest.raises(InvalidProjectExcelUploadError, match="esta vacio"):
            await service.preview_project_excel(
                referencia_id=uuid.uuid4(),
                filename="proyecto.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=b"",
            )

    async def test_preview_rejects_missing_draft(self):
        session = MockSession()
        draft_repository = MockDraftRepository(draft=None)
        audit_repository = MockAuditRepository()
        storage_service = MockStorageService()
        project_repository = MockProjectRepository()

        service = ProyectoExcelImportService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit_repository,
            project_repository=project_repository,
            storage_service=storage_service,
        )

        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        with pytest.raises(ProjectExcelDraftMissingError):
            await service.preview_project_excel(
                referencia_id=uuid.uuid4(),
                filename="proyecto.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=content.read(),
            )

    async def test_preview_persists_in_draft(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert service._draft_repository.saved is True

    async def test_preview_sets_paso_actual(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert service._draft_repository.draft.paso_actual == "fuente-proyecto"

    async def test_preview_triggers_audit_event(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert len(service._audit_repository.events) == 1
        event = service._audit_repository.events[0]
        assert event["accion"] == "EXCEL_PROYECTO_PREVISUALIZADO"


class TestConfirmProjectExcelImport:
    async def test_confirm_materializes_proyecto(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        result = await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert result.proyecto_id is not None
        assert result.resumen.proyecto == 1
        assert result.resumen.fases == 2
        assert result.resumen.actividades == 3

    async def test_confirm_materializes_fases(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        result = await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert len(result.fase_ids) == 2

    async def test_confirm_materializes_actividades(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        result = await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert len(result.actividad_ids) == 3

    async def test_confirm_resolves_programa_id_from_program_draft(self):
        programa_id = uuid.uuid4()
        programa_referencia_id = uuid.uuid4()
        proyecto_referencia_id = uuid.uuid4()
        proyecto_draft = MagicMock(
            id=uuid.uuid4(),
            payload_json={
                "meta": {
                    "referenciaId": str(proyecto_referencia_id),
                    "programaReferenciaId": str(programa_referencia_id),
                    "touchedSteps": ["fuente-proyecto"],
                    "lastInteractionAt": datetime.now(UTC).isoformat(),
                },
                "documental": {},
            },
            paso_actual="fuente-proyecto",
            estado_borrador=EstadoBloque.BORRADOR,
        )
        programa_draft = MagicMock(
            payload_json={
                "meta": {"referenciaId": str(programa_referencia_id)},
                "curricular": {"programa_formacion_id": str(programa_id)},
            },
        )
        session = MockSession()
        draft_repository = MockDraftRepository(proyecto_draft, programa_draft)
        audit_repository = MockAuditRepository()
        storage_service = MockStorageService()
        project_repository = MockProjectRepository()
        service = ProyectoExcelImportService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit_repository,
            project_repository=project_repository,
            storage_service=storage_service,
        )
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=proyecto_referencia_id,
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        await service.confirm_project_excel_import(
            referencia_id=proyecto_referencia_id,
        )

        assert project_repository.created_programa_ids == [programa_id]
        assert proyecto_draft.payload_json["meta"]["programaId"] == str(programa_id)

    async def test_confirm_rejects_missing_preview(self):
        session = MockSession()
        draft_repository = MockDraftRepository(
            MagicMock(
                id=uuid.uuid4(),
                payload_json={
                    "meta": {
                        "programaId": "00000000-0000-0000-0000-000000000000",
                    },
                    "documental": {},
                },
                paso_actual="fuente-proyecto",
                estado_borrador=EstadoBloque.BORRADOR,
            )
        )
        audit_repository = MockAuditRepository()
        storage_service = MockStorageService()
        project_repository = MockProjectRepository()

        service = ProyectoExcelImportService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit_repository,
            project_repository=project_repository,
            storage_service=storage_service,
        )

        with pytest.raises(ProjectExcelMissingPreviewError):
            await service.confirm_project_excel_import(
                referencia_id=uuid.uuid4(),
            )

    async def test_confirm_commits_session(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert service._session.committed is True

    async def test_confirm_stores_excel_in_minio(self):
        storage = MockStorageService()
        session = MockSession()
        draft_repository = MockDraftRepository(
            MagicMock(
                id=uuid.uuid4(),
                payload_json={
                    "meta": {
                        "programaId": "00000000-0000-0000-0000-000000000000",
                    },
                    "documental": {},
                },
                paso_actual="fuente-proyecto",
                estado_borrador=EstadoBloque.BORRADOR,
            )
        )
        audit = MockAuditRepository()
        project_repository = MockProjectRepository()

        service = ProyectoExcelImportService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit,
            project_repository=project_repository,
            storage_service=storage,
        )

        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert storage.document.storage_key.startswith("proyectos-formativos/")

    async def test_confirm_heals_stale_programa_id(self):
        stale_programa_id = uuid.uuid4()
        correct_programa_id = uuid.uuid4()
        programa_referencia_id = uuid.uuid4()
        proyecto_referencia_id = uuid.uuid4()

        proyecto_draft = MagicMock(
            id=uuid.uuid4(),
            payload_json={
                "meta": {
                    "referenciaId": str(proyecto_referencia_id),
                    "programaReferenciaId": str(programa_referencia_id),
                    "programaId": str(stale_programa_id),
                    "touchedSteps": ["fuente-proyecto"],
                    "lastInteractionAt": datetime.now(UTC).isoformat(),
                },
                "documental": {},
            },
            paso_actual="fuente-proyecto",
            estado_borrador=EstadoBloque.BORRADOR,
        )
        programa_draft = MagicMock(
            payload_json={
                "meta": {"referenciaId": str(programa_referencia_id)},
                "curricular": {"programa_formacion_id": str(correct_programa_id)},
            },
        )

        mock_execute_res = MagicMock()
        mock_execute_res.scalar_one_or_none.return_value = None

        session = MockSession()
        session.execute = MagicMock(return_value=mock_execute_res)

        draft_repository = MockDraftRepository(proyecto_draft, programa_draft)
        audit_repository = MockAuditRepository()
        storage_service = MockStorageService()
        project_repository = MockProjectRepository()

        service = ProyectoExcelImportService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit_repository,
            project_repository=project_repository,
            storage_service=storage_service,
        )

        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=proyecto_referencia_id,
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        await service.confirm_project_excel_import(
            referencia_id=proyecto_referencia_id,
        )

        assert project_repository.created_programa_ids == [correct_programa_id]
        assert proyecto_draft.payload_json["meta"]["programaId"] == str(
            correct_programa_id
        )
