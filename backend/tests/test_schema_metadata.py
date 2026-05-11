"""Schema metadata checks for the TASK-02 data model."""

from __future__ import annotations

from sqlalchemy import UniqueConstraint

from src.infrastructure.db import models  # noqa: F401
from src.infrastructure.db.base import Base


def test_phase_one_tables_are_registered() -> None:
    """Ensure the initial Phase 1 tables are present in SQLAlchemy metadata."""

    expected_tables = {
        "actividades_proyecto",
        "borradores_sesion",
        "competencias",
        "conocimientos",
        "criterios_evaluacion",
        "eventos_auditoria",
        "fases_proyecto",
        "programas_formacion",
        "proyectos_formativos",
        "resultados_aprendizaje",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_key_uniqueness_constraints_exist() -> None:
    """Verify uniqueness rules required by the business documents."""

    programas = Base.metadata.tables["programas_formacion"]
    competencias = Base.metadata.tables["competencias"]
    resultados = Base.metadata.tables["resultados_aprendizaje"]
    conocimientos = Base.metadata.tables["conocimientos"]
    criterios = Base.metadata.tables["criterios_evaluacion"]

    constraint_columns = {}
    for table in [programas, competencias, resultados, conocimientos, criterios]:
        unique_cols = set()
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                unique_cols.add(tuple(constraint.columns.keys()))
        for index in table.indexes:
            if index.unique:
                unique_cols.add(tuple([col.name for col in index.columns]))
        constraint_columns[table.name] = unique_cols

    assert ("codigo_programa", "version_programa") in constraint_columns[
        "programas_formacion"
    ]
    assert ("programa_id", "codigo_competencia") in constraint_columns["competencias"]
    assert ("competencia_id", "descripcion") in constraint_columns[
        "resultados_aprendizaje"
    ]
    # Check partial unique index for knowledge and criteria when RAP is provided
    assert (
        "competencia_id",
        "tipo",
        "descripcion",
        "resultado_id",
    ) in constraint_columns["conocimientos"]
    assert (
        "competencia_id",
        "descripcion",
        "resultado_id",
    ) in constraint_columns["criterios_evaluacion"]
