# Backend

Backend FastAPI de la Fase 1 para la aplicacion de guias de aprendizaje SENA.

## Alcance actual

Esta preparacion deja lista la infraestructura de base de datos previa a
`TASK-02`:

- settings con lectura de `backend/.env`,
- SQLAlchemy async para ejecucion de la aplicacion,
- Alembic sync para migraciones,
- metadata declarativa vacia para futuros modelos,
- prueba opt-in de conexion real a PostgreSQL.

No incluye modelos, entidades ni migraciones del dominio.

## Variables de entorno

Crear `backend/.env` desde `backend/.env.example`:

```bash
cp .env.example .env
```

Valores minimos para desarrollo local:

```env
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sena_guias_db"
ALEMBIC_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/sena_guias_db"
```

`DATABASE_URL` usa `asyncpg` para SQLAlchemy async. `ALEMBIC_DATABASE_URL`
usa `psycopg` para Alembic sync.

## Instalar dependencias

```bash
uv sync --python 3.11
```

## Levantar PostgreSQL

Desde la raiz del repositorio:

```bash
docker compose up -d postgres
```

La base local queda disponible en:

```text
postgresql://postgres:postgres@localhost:5432/sena_guias_db
```

Para administrar la base con pgAdmin:

```bash
docker compose up -d postgres pgadmin
```

Acceso local:

- URL: `http://localhost:5050`
- Email: `admin@example.com`
- Password: `admin123`

## Probar conexion real

Desde `backend/`:

```bash
uv run python scripts/check_database_connection.py
```

Salida esperada:

```text
Database connection OK: SELECT 1 returned 1
```

Tambien existe una prueba de integracion opt-in:

```powershell
$env:RUN_DATABASE_TESTS="1"; uv run pytest tests/test_database_connection.py
```

## Ejecutar Alembic

Desde `backend/`:

```bash
uv run alembic current
```

En esta etapa no hay revisiones de dominio. El comando debe iniciar Alembic y
conectar contra PostgreSQL sin crear tablas de programa, competencia, proyecto
u otras entidades de Fase 1.

## Ejecutar pruebas base

```bash
uv run pytest
```
