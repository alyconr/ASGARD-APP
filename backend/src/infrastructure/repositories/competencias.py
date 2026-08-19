"""SQLAlchemy repository for program and competence persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import EstadoBloque, EstadoCampo, TipoFuenteCargue
from src.infrastructure.db.models.curriculum import Competencia, ProgramaFormacion


class CompetenciaRepository:
    """Read and write program formation and competence rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def get_programa(self, programa_id: uuid.UUID) -> ProgramaFormacion | None:
        """Return a program by primary key."""
        return await self._session.get(ProgramaFormacion, programa_id)

    async def get_programa_by_code_version(
        self,
        codigo_programa: str,
        version_programa: str | None,
    ) -> ProgramaFormacion | None:
        """Return the logical program matching code and version."""
        statement = select(ProgramaFormacion).where(
            ProgramaFormacion.codigo_programa == codigo_programa,
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
        codigo_programa: str,
        nombre_programa: str,
        version_programa: str | None,
    ) -> ProgramaFormacion:
        """Create a draft program row for the current wizard flow."""
        programa = ProgramaFormacion(
            codigo_programa=codigo_programa,
            nombre_programa=nombre_programa,
            version_programa=version_programa,
            estado=EstadoBloque.BORRADOR,
            fuente_cargue=TipoFuenteCargue.MIXTO,
        )
        self._session.add(programa)
        await self._session.flush()
        return programa

    async def list_by_programa(self, programa_id: uuid.UUID) -> list[Competencia]:
        """Return all competences linked to the given program."""
        statement = (
            select(Competencia)
            .options(
                selectinload(Competencia.resultados),
                selectinload(Competencia.conocimientos),
                selectinload(Competencia.criterios),
            )
            .where(Competencia.programa_id == programa_id)
            .order_by(Competencia.orden.asc(), Competencia.fecha_creacion.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_for_programa(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> Competencia | None:
        """Return a competence only when it belongs to the given program."""
        statement = (
            select(Competencia)
            .where(Competencia.id == competencia_id)
            .where(Competencia.programa_id == programa_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def code_exists(
        self,
        programa_id: uuid.UUID,
        codigo_competencia: str,
        exclude_competencia_id: uuid.UUID | None = None,
    ) -> bool:
        """Check duplicate competence code inside a program."""
        statement = (
            select(Competencia.id)
            .where(Competencia.programa_id == programa_id)
            .where(
                func.lower(Competencia.codigo_competencia)
                == codigo_competencia.lower(),
            )
        )
        if exclude_competencia_id is not None:
            statement = statement.where(Competencia.id != exclude_competencia_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def add_competencia(
        self,
        programa_id: uuid.UUID,
        codigo_competencia: str,
        nombre_competencia: str,
        orden: int,
    ) -> Competencia:
        """Create a competence for one program."""
        competencia = Competencia(
            programa_id=programa_id,
            codigo_competencia=codigo_competencia,
            nombre_competencia=nombre_competencia,
            orden=orden,
            estado=EstadoBloque.BORRADOR,
            origen_campo=EstadoCampo.MANUAL,
        )
        self._session.add(competencia)
        await self._session.flush()
        return competencia

    async def save_competencia(self, competencia: Competencia) -> Competencia:
        """Flush pending changes to a competence."""
        self._session.add(competencia)
        await self._session.flush()
        return competencia

    async def delete_competencia(self, competencia: Competencia) -> None:
        """Delete a competence row."""
        await self._session.delete(competencia)
        await self._session.flush()
