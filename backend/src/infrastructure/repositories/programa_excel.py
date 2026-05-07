"""Repository for canonical Excel curriculum import persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.enums import (
    EstadoBloque,
    EstadoCampo,
    TipoConocimiento,
    TipoFuenteCargue,
)
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ProgramaFormacion,
    ResultadoAprendizaje,
)


class ProgramaExcelImportRepository:
    """Persist program curriculum rows produced by a canonical Excel workbook."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def get_programa(self, programa_id: uuid.UUID) -> ProgramaFormacion | None:
        """Return a program by id."""
        return await self._session.get(ProgramaFormacion, programa_id)

    async def get_programa_by_code_version(
        self,
        codigo_programa: str,
        version_programa: str | None,
    ) -> ProgramaFormacion | None:
        """Return an existing program matching code and version."""
        statement = select(ProgramaFormacion).where(
            func.lower(ProgramaFormacion.codigo_programa) == codigo_programa.lower(),
        )
        if version_programa is None:
            statement = statement.where(ProgramaFormacion.version_programa.is_(None))
        else:
            statement = statement.where(
                ProgramaFormacion.version_programa == version_programa,
            )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def add_programa(
        self,
        *,
        codigo_programa: str,
        nombre_programa: str,
        version_programa: str | None,
    ) -> ProgramaFormacion:
        """Create a program row from the canonical Excel workbook."""
        programa = ProgramaFormacion(
            codigo_programa=codigo_programa,
            nombre_programa=nombre_programa,
            version_programa=version_programa,
            estado=EstadoBloque.BORRADOR,
            fuente_cargue=TipoFuenteCargue.EXCEL_CANONICO,
        )
        self._session.add(programa)
        await self._session.flush()
        return programa

    async def list_competencias(self, programa_id: uuid.UUID) -> list[Competencia]:
        """List all competences of a program."""
        statement = (
            select(Competencia)
            .where(Competencia.programa_id == programa_id)
            .order_by(Competencia.orden.asc(), Competencia.fecha_creacion.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def competencia_code_exists(
        self,
        *,
        programa_id: uuid.UUID,
        codigo_competencia: str,
    ) -> bool:
        """Return whether a competence code already exists in a program."""
        statement = (
            select(Competencia.id)
            .where(Competencia.programa_id == programa_id)
            .where(
                func.lower(Competencia.codigo_competencia)
                == codigo_competencia.lower(),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def resultado_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        descripcion: str,
    ) -> bool:
        """Return whether a result description already exists."""
        statement = (
            select(ResultadoAprendizaje.id)
            .where(ResultadoAprendizaje.competencia_id == competencia_id)
            .where(func.lower(ResultadoAprendizaje.descripcion) == descripcion.lower())
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def conocimiento_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        tipo: TipoConocimiento,
        descripcion: str,
    ) -> bool:
        """Return whether a knowledge item already exists."""
        statement = (
            select(Conocimiento.id)
            .where(Conocimiento.competencia_id == competencia_id)
            .where(Conocimiento.tipo == tipo)
            .where(func.lower(Conocimiento.descripcion) == descripcion.lower())
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def criterio_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        descripcion: str,
    ) -> bool:
        """Return whether a criterion description already exists."""
        statement = (
            select(CriterioEvaluacion.id)
            .where(CriterioEvaluacion.competencia_id == competencia_id)
            .where(func.lower(CriterioEvaluacion.descripcion) == descripcion.lower())
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def add_competencia(
        self,
        *,
        programa_id: uuid.UUID,
        codigo_competencia: str,
        nombre_competencia: str,
        orden: int | None,
    ) -> Competencia:
        """Create a competence imported from Excel."""
        competencia = Competencia(
            programa_id=programa_id,
            codigo_competencia=codigo_competencia,
            nombre_competencia=nombre_competencia,
            orden=orden,
            estado=EstadoBloque.BORRADOR,
            origen_campo=EstadoCampo.VALIDADO,
        )
        self._session.add(competencia)
        await self._session.flush()
        return competencia

    async def add_resultado(
        self,
        *,
        competencia_id: uuid.UUID,
        codigo_resultado: str | None,
        descripcion: str,
        orden: int | None,
    ) -> ResultadoAprendizaje:
        """Create a learning result imported from Excel."""
        resultado = ResultadoAprendizaje(
            competencia_id=competencia_id,
            codigo_resultado=codigo_resultado,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.VALIDADO,
        )
        self._session.add(resultado)
        await self._session.flush()
        return resultado

    async def add_conocimiento(
        self,
        *,
        competencia_id: uuid.UUID,
        tipo: TipoConocimiento,
        descripcion: str,
        orden: int | None,
    ) -> Conocimiento:
        """Create a knowledge row imported from Excel."""
        conocimiento = Conocimiento(
            competencia_id=competencia_id,
            tipo=tipo,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.VALIDADO,
        )
        self._session.add(conocimiento)
        await self._session.flush()
        return conocimiento

    async def add_criterio(
        self,
        *,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int | None,
    ) -> CriterioEvaluacion:
        """Create an evaluation criterion imported from Excel."""
        criterio = CriterioEvaluacion(
            competencia_id=competencia_id,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.VALIDADO,
        )
        self._session.add(criterio)
        await self._session.flush()
        return criterio
