# SENA Guia Aprendizaje App

Base tecnica inicial de la Fase 1 para la aplicacion web de construccion de guias de aprendizaje SENA.

## Stack aprobado

- Frontend: Next.js + React + TypeScript + Tailwind CSS
- Backend: FastAPI
- Base de datos: PostgreSQL
- Arquitectura: frontend y backend desacoplados, organizacion modular por dominio

## Estructura inicial

```text
.
|- backend/
|  |- pyproject.toml
|  \- src/
|     |- application/
|     |- domain/
|     |- infrastructure/
|     \- interfaces/
|- docs/
|- frontend/
|  |- package.json
|  |- src/
|  |  |- app/
|  |  |- components/
|  |  |- features/
|  |  |- lib/
|  |  |- services/
|  |  |- types/
|  |  \- validators/
|  \- public/
\- scripts/
```

## Requisitos locales

- Node.js 22+
- npm 10+
- Python 3.11
- `uv` para gestionar el entorno Python
- Docker Desktop o PostgreSQL 15+ disponible localmente

## Variables de entorno

1. Copiar `frontend/.env.example` a `frontend/.env.local`
2. Copiar `backend/.env.example` a `backend/.env`

El backend requiere estas URLs minimas:

```env
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sena_guias_db"
ALEMBIC_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/sena_guias_db"
```

## Instalacion

### Frontend

```bash
cd frontend
npm install
```

En PowerShell sobre Windows puede ser necesario usar `npm.cmd install`.

### Backend

```bash
cd backend
uv sync --python 3.11
```

Si tu entorno usa `pyenv-win`, asegurate de tener Python 3.11 disponible.

## Ejecucion local

### PostgreSQL

```bash
docker compose up -d postgres
```

El servicio crea la base `sena_guias_db` en `localhost:5432`.

### pgAdmin

```bash
docker compose up -d postgres pgadmin
```

pgAdmin queda disponible en `http://localhost:5050`.

Credenciales por defecto:

- Email: `admin@example.com`
- Password: `admin123`

Si necesitas cambiarlas sin modificar el compose, define
`PGADMIN_DEFAULT_EMAIL` y `PGADMIN_DEFAULT_PASSWORD` antes de levantar el
servicio.

### Frontend

```bash
cd frontend
npm run dev
```

Aplicacion disponible en `http://localhost:3000`.

### Backend

```bash
cd backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API disponible en `http://localhost:8000` y healthcheck en `http://localhost:8000/api/v1/health`.

## Calidad base

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
```

### Backend

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Base de datos y Alembic

Para validar conexion real a PostgreSQL:

```bash
cd backend
uv run python scripts/check_database_connection.py
```

Para verificar que Alembic arranca contra PostgreSQL:

```bash
cd backend
uv run alembic current
```

Esta preparacion no crea modelos ni migraciones del dominio; eso corresponde a
`TASK-02`.

## Alcance de esta base

Esta iteracion implementa unicamente `TASK-01`:

- estructura inicial del repositorio,
- configuracion de frontend y backend,
- configuracion de lint y formato,
- variables de entorno base,
- endpoint minimo de salud para verificar el backend.

No incluye logica de negocio, entidades del dominio, wizard ni persistencia funcional.
