"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.config.settings import get_settings
from src.infrastructure.runtime import configure_asyncio_event_loop_policy

configure_asyncio_event_loop_policy()

from src.interfaces.http.controllers.competencias import (
    router as competencias_router,
)
from src.interfaces.http.controllers.conocimientos_proceso import (
    router as conocimientos_proceso_router,
)
from src.interfaces.http.controllers.conocimientos_saber import (
    router as conocimientos_saber_router,
)
from src.interfaces.http.controllers.criterios import (
    router as criterios_router,
)
from src.interfaces.http.controllers.drafts import router as drafts_router
from src.interfaces.http.controllers.health import router as health_router
from src.interfaces.http.controllers.pendientes_curriculares import (
    router as pendientes_curriculares_router,
)
from src.interfaces.http.controllers.planeacion import (
    router as planeacion_router,
)
from src.interfaces.http.controllers.programa_cierre import (
    router as programa_cierre_router,
)
from src.interfaces.http.controllers.programa_documentos import (
    router as programa_documentos_router,
)
from src.interfaces.http.controllers.programa_excel import (
    router as programa_excel_router,
)
from src.interfaces.http.controllers.proyecto_cargue import (
    router as proyecto_cargue_router,
)
from src.interfaces.http.controllers.proyecto_documentos import (
    router as proyecto_documentos_router,
)
from src.interfaces.http.controllers.proyecto_excel import (
    router as proyecto_excel_router,
)
from src.interfaces.http.controllers.proyecto_gate import (
    router as proyecto_gate_router,
)
from src.interfaces.http.controllers.resultados_aprendizaje import (
    router as resultados_aprendizaje_router,
)


def create_application() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(drafts_router)
    application.include_router(programa_documentos_router)
    application.include_router(programa_cierre_router)
    application.include_router(proyecto_gate_router)
    application.include_router(proyecto_documentos_router)
    application.include_router(proyecto_excel_router)
    application.include_router(programa_excel_router)
    application.include_router(competencias_router)
    application.include_router(resultados_aprendizaje_router)
    application.include_router(conocimientos_saber_router)
    application.include_router(conocimientos_proceso_router)
    application.include_router(criterios_router)
    application.include_router(pendientes_curriculares_router)
    application.include_router(proyecto_cargue_router)
    application.include_router(planeacion_router)

    return application


app = create_application()
