"""Canonical Excel preview and import service for project TASK-19."""

from __future__ import annotations

import io
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from openpyxl import load_workbook

from src.application.dto.proyecto_excel import (
    ExcelActividadPreviewDTO,
    ExcelFasePreviewDTO,
    ExcelPendingSummaryDTO,
    ExcelPreviewSummaryDTO,
    ExcelProjectPreviewDTO,
    ExcelValidationIssueDTO,
    ProyectoExcelImportDTO,
    ProyectoExcelPreviewDTO,
)
from src.application.dto.programa_documentos import StoredDocumentDTO
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, EstadoCampo
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.proyecto import ActividadProyecto, FaseProyecto, ProyectoFormativo

CANONICAL_SHEETS: dict[str, list[str]] = {
    "Proyecto": [
        "codigo_proyecto",
        "nombre_proyecto",
        "version_proyecto",
        "programa_referencia",
        "observaciones",
    ],
    "Fases": [
        "fase_id",
        "nombre_fase",
        "orden",
        "descripcion",
        "observaciones",
    ],
    "Actividades": [
        "fase_id",
        "descripcion",
        "orden",
        "observaciones",
    ],
}

EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ProjectExcelDraftMissingError(Exception):
    """Raised when an Excel import has no current wizard draft."""


class InvalidProjectExcelUploadError(Exception):
    """Raised when the upload is not an accepted canonical workbook."""


class ProjectExcelValidationError(Exception):
    """Raised when a workbook cannot be imported after validation."""


class ProjectExcelMissingPreviewError(Exception):
    """Raised when import confirmation has no valid preview to confirm."""


class ProjectExcelStorageMissingError(Exception):
    """Raised when the stored workbook cannot be read for confirmation."""


@dataclass(frozen=True)
class ProjectRow:
    codigo_proyecto: str
    nombre_proyecto: str
    version_proyecto: str
    raw: dict[str, object]


@dataclass(frozen=True)
class FaseRow:
    fase_id: str
    nombre_fase: str
    orden: int | None
    raw: dict[str, object]


@dataclass(frozen=True)
class ActividadRow:
    fase_id: str
    descripcion: str
    orden: int | None
    raw: dict[str, object]


@dataclass(frozen=True)
class CanonicalWorkbook:
    proyecto: ProjectRow | None
    fases: list[FaseRow]
    actividades: list[ActividadRow]
    errores: list[ExcelValidationIssueDTO]

    @property
    def is_valid(self) -> bool:
        """Return whether the workbook can proceed to preview or import."""
        return len(self.errores) == 0 and self.proyecto is not None


class DocumentStorageProtocol(Protocol):
    """Storage behavior required by the canonical Excel service."""

    async def save_excel(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> StoredDocumentDTO:
        """Persist an Excel file and return object metadata."""

    async def read_excel(self, *, key: str) -> bytes:
        """Read a stored Excel file."""


class DraftRepositoryProtocol(Protocol):
    """Draft repository dependency used to associate imports to the wizard."""

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the current logical draft for a reference."""

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Persist modifications on an existing draft row."""


class AuditRepositoryProtocol(Protocol):
    """Audit dependency for relevant import events."""

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> object:
        """Persist a basic audit event."""


class ProjectRepositoryProtocol(Protocol):
    """Repository behavior required by the project Excel import service."""

    async def create_proyecto(
        self,
        *,
        programa_id: uuid.UUID,
        codigo_proyecto: str,
        nombre_proyecto: str,
        version_proyecto: str,
    ) -> ProyectoFormativo:
        """Create a project row."""

    async def create_fase(
        self,
        *,
        proyecto_id: uuid.UUID,
        nombre_fase: str,
        orden: int | None,
    ) -> FaseProyecto:
        """Create a project phase."""

    async def create_actividad(
        self,
        *,
        fase_id: uuid.UUID,
        descripcion: str,
        orden: int | None,
    ) -> ActividadProyecto:
        """Create a project activity."""


class AsyncSessionProtocol(Protocol):
    """Subset of async session behavior required by this service."""

    async def commit(self) -> None:
        """Commit the current transaction."""

    async def refresh(self, instance: object) -> None:
        """Refresh the provided ORM instance."""


class ProyectoExcelImportService:
    """Validate, preview and confirm canonical Excel project imports."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
        project_repository: ProjectRepositoryProtocol,
        storage_service: DocumentStorageProtocol,
    ) -> None:
        """Initialize the service with explicit infrastructure ports."""
        self._session = session
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository
        self._project_repository = project_repository
        self._storage_service = storage_service

    async def preview_project_excel(
        self,
        *,
        referencia_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> ProyectoExcelPreviewDTO:
        """Store and validate a canonical Excel workbook without relational writes."""
        _validate_excel_upload(filename=filename, content=content)
        draft = await self._get_project_draft(referencia_id)
        workbook = parse_canonical_workbook(content)
        stored_document: StoredDocumentDTO | None = None

        if workbook.is_valid:
            stored_document = await self._storage_service.save_excel(
                key=_build_excel_storage_key(referencia_id, filename),
                content=content,
                content_type=content_type or EXCEL_CONTENT_TYPE,
                original_filename=filename,
            )

        preview = _build_preview_dto(
            referencia_id=referencia_id,
            workbook=workbook,
            document=stored_document,
        )
        draft.payload_json = _merge_excel_preview_into_payload(
            payload=draft.payload_json,
            preview=preview,
        )
        draft.paso_actual = "fuente-proyecto"
        draft.estado_borrador = EstadoBloque.BORRADOR
        await self._draft_repository.save(draft)
        await self._audit_repository.add_event(
            entidad="BorradorSesion",
            entidad_id=draft.id,
            accion="EXCEL_PROYECTO_PREVISUALIZADO",
            detalle={
                "referencia_id": str(referencia_id),
                "estado_validacion": preview.estado_validacion,
                "errores": len(preview.errores),
            },
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return preview

    async def confirm_project_excel_import(
        self,
        *,
        referencia_id: uuid.UUID,
    ) -> ProyectoExcelImportDTO:
        """Materialize a previously validated canonical workbook."""
        draft = await self._get_project_draft(referencia_id)
        preview_payload = _get_valid_excel_preview_payload(draft.payload_json)
        document_payload = _as_record(preview_payload.get("documento"))
        storage_key = _read_string(document_payload or {}, "storage_key")
        if not storage_key:
            raise ProjectExcelMissingPreviewError(
                "El borrador no tiene un Excel canonico validado para confirmar",
            )

        try:
            content = await self._storage_service.read_excel(key=storage_key)
        except FileNotFoundError as error:
            raise ProjectExcelStorageMissingError(
                "El Excel canonico validado ya no existe en MinIO",
            ) from error

        workbook = parse_canonical_workbook(content)
        if not workbook.is_valid or workbook.proyecto is None:
            raise ProjectExcelValidationError(
                "El Excel canonico almacenado ya no supera la validacion",
            )

        import_result = await self._materialize_workbook(
            referencia_id=referencia_id,
            draft=draft,
            workbook=workbook,
        )
        draft.payload_json = _merge_excel_import_into_payload(
            payload=draft.payload_json,
            result=import_result,
        )
        await self._draft_repository.save(draft)
        await self._audit_repository.add_event(
            entidad="ProyectoFormativo",
            entidad_id=import_result.proyecto_id,
            accion="EXCEL_PROYECTO_IMPORTADO",
            detalle={
                "referencia_id": str(referencia_id),
                "fases": import_result.resumen.fases,
                "actividades": import_result.resumen.actividades,
            },
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return import_result

    async def _get_project_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROYECTO,
            referencia_id,
        )
        if draft is None:
            raise ProjectExcelDraftMissingError(
                "No existe un borrador de proyecto para asociar el Excel",
            )
        return draft

    async def _materialize_workbook(
        self,
        *,
        referencia_id: uuid.UUID,
        draft: BorradorSesion,
        workbook: CanonicalWorkbook,
    ) -> ProyectoExcelImportDTO:
        if workbook.proyecto is None:
            raise ProjectExcelValidationError("La hoja Proyecto esta vacia")

        proyecto = await self._project_repository.create_proyecto(
            programa_id=uuid.UUID(draft.payload_json.get("meta", {}).get("programaId", "00000000-0000-0000-0000-000000000000")),
            codigo_proyecto=workbook.proyecto.codigo_proyecto,
            nombre_proyecto=workbook.proyecto.nombre_proyecto,
            version_proyecto=workbook.proyecto.version_proyecto,
        )
        await self._session.refresh(proyecto)

        fase_by_excel_id: dict[str, uuid.UUID] = {}
        fase_ids: list[uuid.UUID] = []
        actividad_ids: list[uuid.UUID] = []

        for fase_row in workbook.fases:
            fase = await self._project_repository.create_fase(
                proyecto_id=proyecto.id,
                nombre_fase=fase_row.nombre_fase,
                orden=fase_row.orden,
            )
            await self._session.refresh(fase)
            fase_by_excel_id[fase_row.fase_id] = fase.id
            fase_ids.append(fase.id)

        for actividad_row in workbook.actividades:
            fase_id = fase_by_excel_id.get(actividad_row.fase_id)
            if fase_id is None:
                raise ProjectExcelValidationError(
                    f"Actividad en fila {actividad_row.raw.get('_row_index')} "
                    f"referencia fase_id '{actividad_row.fase_id}' no encontrada en Fases",
                )
            actividad = await self._project_repository.create_actividad(
                fase_id=fase_id,
                descripcion=actividad_row.descripcion,
                orden=actividad_row.orden,
            )
            await self._session.refresh(actividad)
            actividad_ids.append(actividad.id)

        return ProyectoExcelImportDTO(
            referencia_id=referencia_id,
            proyecto_id=proyecto.id,
            fase_ids=fase_ids,
            actividad_ids=actividad_ids,
            resumen=_build_summary(workbook),
            pendientes_resumen=ExcelPendingSummaryDTO(total=0),
        )


def parse_canonical_workbook(content: bytes) -> CanonicalWorkbook:
    """Read and validate the canonical project workbook contract."""
    errores: list[ExcelValidationIssueDTO] = []
    try:
        workbook = load_workbook(
            filename=io.BytesIO(content),
            read_only=True,
            data_only=True,
        )
    except Exception as error:
        return CanonicalWorkbook(
            proyecto=None,
            fases=[],
            actividades=[],
            errores=[
                ExcelValidationIssueDTO(
                    hoja="Workbook",
                    fila=None,
                    campo=None,
                    mensaje=f"No fue posible leer el Excel del proyecto: {error}",
                ),
            ],
        )

    missing_sheets = [
        sheet_name
        for sheet_name in CANONICAL_SHEETS
        if sheet_name not in workbook.sheetnames
    ]
    for sheet_name in missing_sheets:
        errores.append(
            ExcelValidationIssueDTO(
                hoja=sheet_name,
                fila=None,
                campo=None,
                mensaje="Hoja obligatoria faltante",
            ),
        )
    if missing_sheets:
        return CanonicalWorkbook(None, [], [], errores)

    rows_by_sheet: dict[str, list[dict[str, object]]] = {}
    for sheet_name, expected_headers in CANONICAL_SHEETS.items():
        sheet = workbook[sheet_name]
        header_values = [
            _cell_to_string(value)
            for value in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
        ]
        if header_values != expected_headers:
            errores.append(
                ExcelValidationIssueDTO(
                    hoja=sheet_name,
                    fila=1,
                    campo=None,
                    mensaje="Encabezados invalidos o en orden distinto al canonico",
                ),
            )
            continue

        sheet_rows: list[dict[str, object]] = []
        for row_index, values in enumerate(
            sheet.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            if all(_cell_to_string(value) == "" for value in values):
                continue
            record: dict[str, object] = {
                header: value
                for header, value in zip(expected_headers, values, strict=False)
            }
            record["_row_index"] = row_index
            sheet_rows.append(record)
        rows_by_sheet[sheet_name] = sheet_rows

    if errores:
        return CanonicalWorkbook(None, [], [], errores)

    proyecto = _parse_proyecto(rows_by_sheet["Proyecto"], errores)
    fases = _parse_fases(rows_by_sheet["Fases"], errores)
    actividades = _parse_actividades(rows_by_sheet["Actividades"], errores)

    _validate_cross_references(
        fases=fases,
        actividades=actividades,
        errores=errores,
    )

    return CanonicalWorkbook(
        proyecto=proyecto,
        fases=fases,
        actividades=actividades,
        errores=errores,
    )


def _parse_proyecto(
    rows: list[dict[str, object]],
    errores: list[ExcelValidationIssueDTO],
) -> ProjectRow | None:
    if len(rows) != 1:
        errores.append(
            ExcelValidationIssueDTO(
                hoja="Proyecto",
                fila=None,
                campo=None,
                mensaje="La hoja Proyecto debe tener exactamente una fila de datos",
            ),
        )
        return None

    row = rows[0]
    codigo = _required_string(row, "Proyecto", "codigo_proyecto", errores)
    nombre = _required_string(row, "Proyecto", "nombre_proyecto", errores)
    version = _required_string(row, "Proyecto", "version_proyecto", errores)
    if codigo is None or nombre is None or version is None:
        return None
    return ProjectRow(codigo, nombre, version, _public_record(row))


def _parse_fases(
    rows: list[dict[str, object]],
    errores: list[ExcelValidationIssueDTO],
) -> list[FaseRow]:
    parsed: list[FaseRow] = []
    for row in rows:
        fase_id = _required_string(row, "Fases", "fase_id", errores)
        nombre = _required_string(row, "Fases", "nombre_fase", errores)
        orden = _optional_int(row, "Fases", "orden", errores)
        if fase_id is None or nombre is None:
            continue
        parsed.append(
            FaseRow(
                fase_id=fase_id,
                nombre_fase=nombre,
                orden=orden,
                raw=_public_record(row),
            ),
        )
    return parsed


def _parse_actividades(
    rows: list[dict[str, object]],
    errores: list[ExcelValidationIssueDTO],
) -> list[ActividadRow]:
    parsed: list[ActividadRow] = []
    for row in rows:
        fase_id = _required_string(row, "Actividades", "fase_id", errores)
        descripcion = _required_string(row, "Actividades", "descripcion", errores)
        orden = _optional_int(row, "Actividades", "orden", errores)
        if fase_id is None or descripcion is None:
            continue
        parsed.append(
            ActividadRow(
                fase_id=fase_id,
                descripcion=descripcion,
                orden=orden,
                raw=_public_record(row),
            ),
        )
    return parsed


def _validate_cross_references(
    *,
    fases: list[FaseRow],
    actividades: list[ActividadRow],
    errores: list[ExcelValidationIssueDTO],
) -> None:
    fase_ids = {row.fase_id for row in fases}
    for actividad in actividades:
        if actividad.fase_id not in fase_ids:
            errores.append(
                ExcelValidationIssueDTO(
                    hoja="Actividades",
                    fila=_row_index(actividad.raw),
                    campo="fase_id",
                    mensaje="fase_id no existe en hoja Fases",
                ),
            )


def _validate_excel_upload(*, filename: str, content: bytes) -> None:
    if not filename.strip():
        raise InvalidProjectExcelUploadError("El archivo Excel es obligatorio")
    if not filename.lower().endswith(".xlsx"):
        raise InvalidProjectExcelUploadError("Solo se aceptan archivos .xlsx")
    if not content:
        raise InvalidProjectExcelUploadError("El Excel seleccionado esta vacio")


def _build_preview_dto(
    *,
    referencia_id: uuid.UUID,
    workbook: CanonicalWorkbook,
    document: StoredDocumentDTO | None,
) -> ProyectoExcelPreviewDTO:
    return ProyectoExcelPreviewDTO(
        referencia_id=referencia_id,
        documento=document,
        valid=workbook.is_valid,
        estado_validacion="VALIDO" if workbook.is_valid else "INVALIDO",
        resumen=_build_summary(workbook),
        proyecto=(
            ExcelProjectPreviewDTO(
                codigo_proyecto=workbook.proyecto.codigo_proyecto,
                nombre_proyecto=workbook.proyecto.nombre_proyecto,
                version_proyecto=workbook.proyecto.version_proyecto,
            )
            if workbook.proyecto is not None
            else None
        ),
        fases=[
            ExcelFasePreviewDTO(
                fase_id=row.fase_id,
                nombre_fase=row.nombre_fase,
                orden=row.orden,
                actividades=sum(
                    1 for a in workbook.actividades if a.fase_id == row.fase_id
                ),
            )
            for row in workbook.fases
        ],
        pendientes_resumen=ExcelPendingSummaryDTO(total=0),
        errores=workbook.errores,
    )


def _build_summary(workbook: CanonicalWorkbook) -> ExcelPreviewSummaryDTO:
    return ExcelPreviewSummaryDTO(
        proyecto=1 if workbook.proyecto is not None else 0,
        fases=len(workbook.fases),
        actividades=len(workbook.actividades),
    )


def _merge_excel_preview_into_payload(
    *,
    payload: dict[str, object],
    preview: ProyectoExcelPreviewDTO,
) -> dict[str, object]:
    next_payload = dict(payload)
    now = datetime.now(UTC).isoformat()
    meta = _as_record(next_payload.get("meta")) or {}
    next_payload["meta"] = {
        **meta,
        "lastInteractionAt": now,
        "touchedSteps": _append_touched_step(
            meta.get("touchedSteps"),
            "fuente-proyecto",
        ),
    }
    documental = _as_record(next_payload.get("documental")) or {}
    documental["fuente_estructurada"] = _preview_to_payload(preview, updated_at=now)
    next_payload["documental"] = documental
    return next_payload


def _merge_excel_import_into_payload(
    *,
    payload: dict[str, object],
    result: ProyectoExcelImportDTO,
) -> dict[str, object]:
    next_payload = dict(payload)
    now = datetime.now(UTC).isoformat()
    documental = _as_record(next_payload.get("documental")) or {}
    excel_payload = _as_record(documental.get("fuente_estructurada")) or {}
    excel_payload["confirmacion"] = {
        "estado": "IMPORTADO",
        "confirmed_at": now,
        "proyecto_id": str(result.proyecto_id),
        "fase_ids": [str(item) for item in result.fase_ids],
        "actividad_ids": [str(item) for item in result.actividad_ids],
        "pendientes_resumen": {
            "total": result.pendientes_resumen.total,
        },
    }
    documental["fuente_estructurada"] = excel_payload
    next_payload["documental"] = documental

    if result.resumen.proyecto == 1:
        preview = _as_record(excel_payload.get("preview")) or {}
        proyecto_p = _as_record(preview.get("proyecto")) or {}
        next_payload["proyecto"] = {
            **(_as_record(next_payload.get("proyecto")) or {}),
            "codigo_proyecto": _read_string(proyecto_p, "codigo_proyecto"),
            "nombre_proyecto": _read_string(proyecto_p, "nombre_proyecto"),
            "version_proyecto": _read_string(proyecto_p, "version_proyecto"),
        }

    next_payload["estructura"] = {
        "fases": [
            {"fase_id": str(fid), "estado": "IMPORTADO"}
            for fid in result.fase_ids
        ],
        "actividades": [
            {"actividad_id": str(aid), "estado": "IMPORTADO"}
            for aid in result.actividad_ids
        ],
        "excel_import": {
            "estado": "IMPORTADO",
            "updated_at": now,
            "resumen": {
                "proyecto": result.resumen.proyecto,
                "fases": result.resumen.fases,
                "actividades": result.resumen.actividades,
            },
        },
    }
    return next_payload


def _preview_to_payload(
    preview: ProyectoExcelPreviewDTO,
    *,
    updated_at: str,
) -> dict[str, object]:
    return {
        "documento": _document_to_payload(preview.documento),
        "preview": {
            "valid": preview.valid,
            "estado_validacion": preview.estado_validacion,
            "resumen": {
                "proyecto": preview.resumen.proyecto,
                "fases": preview.resumen.fases,
                "actividades": preview.resumen.actividades,
            },
            "proyecto": (
                {
                    "codigo_proyecto": preview.proyecto.codigo_proyecto,
                    "nombre_proyecto": preview.proyecto.nombre_proyecto,
                    "version_proyecto": preview.proyecto.version_proyecto,
                }
                if preview.proyecto is not None
                else None
            ),
            "fases": [
                {
                    "fase_id": item.fase_id,
                    "nombre_fase": item.nombre_fase,
                    "orden": item.orden,
                    "actividades": item.actividades,
                }
                for item in preview.fases
            ],
            "pendientes_resumen": {
                "total": preview.pendientes_resumen.total,
            },
            "errores": [
                {
                    "hoja": e.hoja,
                    "fila": e.fila,
                    "campo": e.campo,
                    "mensaje": e.mensaje,
                }
                for e in preview.errores
            ],
        },
        "updated_at": updated_at,
    }


def _get_valid_excel_preview_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    documental = _as_record(payload.get("documental")) or {}
    excel = _as_record(documental.get("fuente_estructurada")) or {}
    preview = _as_record(excel.get("preview"))
    if preview is None:
        raise ProjectExcelMissingPreviewError("No se encontro preview de importacion en el borrador")
    return {
        "documento": _as_record(excel.get("documento")) or {},
        "preview": preview,
    }


def _as_record(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    return None


def _read_string(record: dict[str, object], key: str) -> str:
    val = record.get(key)
    return val if isinstance(val, str) else ""


def _document_to_payload(document: object | None) -> dict[str, object] | None:
    if document is None:
        return None
    if isinstance(document, dict):
        return document
    return {}


def _append_touched_step(steps: list[object] | None, step_id: str) -> list[str]:
    if not isinstance(steps, list):
        return [step_id]
    result = [s for s in steps if isinstance(s, str)]
    if step_id not in result:
        result.append(step_id)
    return result


def _cell_to_string(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _required_string(
    row: dict[str, object],
    hoja: str,
    campo: str,
    errores: list[ExcelValidationIssueDTO],
) -> str | None:
    value = row.get(campo)
    text = str(value).strip() if value is not None else ""
    if not text:
        errores.append(
            ExcelValidationIssueDTO(
                hoja=hoja,
                fila=_row_index(row),
                campo=campo,
                mensaje=f"Campo obligatorio '{campo}' faltante o vacio",
            ),
        )
        return None
    return text


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _optional_int(
    row: dict[str, object],
    hoja: str,
    campo: str,
    errores: list[ExcelValidationIssueDTO],
) -> int | None:
    value = row.get(campo)
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        errores.append(
            ExcelValidationIssueDTO(
                hoja=hoja,
                fila=_row_index(row),
                campo=campo,
                mensaje=f"Valor invalido para campo numerico '{campo}'",
            ),
        )
        return None


def _row_index(row: dict[str, object]) -> int | None:
    val = row.get("_row_index")
    if isinstance(val, int):
        return val
    return None


def _public_record(row: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in row.items() if not k.startswith("_")}
