"""Seed script to populate initial RBAC roles, coordinations, specialties, users, and teams."""

import asyncio
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from sqlalchemy import select
from src.domain.shared.enums import EstadoEquipo, RolUsuario
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
)
from src.infrastructure.db.session import async_session_factory
from src.infrastructure.security.password import hash_password


async def seed() -> None:
    async with async_session_factory() as session:
        print("1. Ensuring system roles...")
        roles_data = [
            (RolUsuario.SUPERADMIN, "Superadministrador"),
            (RolUsuario.ADMIN, "Administrador Pedagógico"),
            (RolUsuario.LIDER_EQUIPO_EJECUTOR, "Líder de Equipo Ejecutor"),
            (RolUsuario.USUARIO_ADICIONAL, "Usuario de Apoyo en Equipo Ejecutor"),
        ]
        role_map: dict[str, Rol] = {}
        for role_name, desc in roles_data:
            stmt = select(Rol).where(Rol.nombre == role_name.value)
            res = await session.execute(stmt)
            role = res.scalar_one_or_none()
            if not role:
                role = Rol(id=uuid.uuid4(), nombre=role_name.value, descripcion=desc)
                session.add(role)
                await session.flush()
            role_map[role_name.value] = role

        print("2. Ensuring Coordination and Specialty...")
        coord_stmt = select(Coordinacion).where(Coordinacion.codigo == "COORD-TELEINFO")
        coord_res = await session.execute(coord_stmt)
        coordinacion = coord_res.scalar_one_or_none()
        if not coordinacion:
            coordinacion = Coordinacion(
                id=uuid.uuid4(),
                codigo="COORD-TELEINFO",
                nombre="Coordinación Teleinformática",
                activo=True,
            )
            session.add(coordinacion)
            await session.flush()

        esp_stmt = select(Especialidad).where(
            Especialidad.coordinacion_id == coordinacion.id,
            Especialidad.codigo == "ESP-REDES",
        )
        esp_res = await session.execute(esp_stmt)
        especialidad = esp_res.scalar_one_or_none()
        if not especialidad:
            especialidad = Especialidad(
                id=uuid.uuid4(),
                coordinacion_id=coordinacion.id,
                codigo="ESP-REDES",
                nombre="Redes de Datos",
                activo=True,
            )
            session.add(especialidad)
            await session.flush()

        print("3. Ensuring Demo Users...")
        default_pw = hash_password("password123")
        users_spec = [
            {
                "email": "admin.pedagogico@sena.edu.co",
                "nombre": "Admin",
                "apellido": "Pedagógico",
                "roles": [RolUsuario.ADMIN.value],
                "coord_id": coordinacion.id,
                "esp_id": especialidad.id,
            },
            {
                "email": "lider.redes1@sena.edu.co",
                "nombre": "Líder",
                "apellido": "Redes 01",
                "roles": [RolUsuario.LIDER_EQUIPO_EJECUTOR.value],
                "coord_id": coordinacion.id,
                "esp_id": especialidad.id,
            },
            {
                "email": "lider.redes2@sena.edu.co",
                "nombre": "Líder",
                "apellido": "Redes 02",
                "roles": [RolUsuario.LIDER_EQUIPO_EJECUTOR.value],
                "coord_id": coordinacion.id,
                "esp_id": especialidad.id,
            },
            {
                "email": "apoyo.redes1@sena.edu.co",
                "nombre": "Apoyo",
                "apellido": "Redes 01",
                "roles": [RolUsuario.USUARIO_ADICIONAL.value],
                "coord_id": coordinacion.id,
                "esp_id": especialidad.id,
            },
        ]

        user_map: dict[str, Usuario] = {}
        for spec in users_spec:
            u_stmt = select(Usuario).where(Usuario.email == spec["email"])
            u_res = await session.execute(u_stmt)
            user = u_res.scalar_one_or_none()
            if not user:
                user = Usuario(
                    id=uuid.uuid4(),
                    email=spec["email"],
                    password_hash=default_pw,
                    nombre=spec["nombre"],
                    apellido=spec["apellido"],
                    coordinacion_id=spec["coord_id"],
                    especialidad_id=spec["esp_id"],
                    activo=True,
                )
                session.add(user)
                await session.flush()
            user.roles = [role_map[r] for r in spec["roles"]]
            user_map[spec["email"]] = user

        print("4. Ensuring Executing Teams...")
        # Team 1
        t1_stmt = select(EquipoEjecutor).where(EquipoEjecutor.nombre == "Equipo Redes 01")
        t1_res = await session.execute(t1_stmt)
        team1 = t1_res.scalar_one_or_none()
        if not team1:
            team1 = EquipoEjecutor(
                id=uuid.uuid4(),
                nombre="Equipo Redes 01",
                coordinacion_id=coordinacion.id,
                especialidad_id=especialidad.id,
                lider_id=user_map["lider.redes1@sena.edu.co"].id,
                estado=EstadoEquipo.ACTIVO,
            )
            session.add(team1)
            await session.flush()

        # Add member to Team 1
        m_stmt = select(EquipoEjecutorMiembro).where(
            EquipoEjecutorMiembro.equipo_id == team1.id,
            EquipoEjecutorMiembro.usuario_id == user_map["apoyo.redes1@sena.edu.co"].id,
        )
        m_res = await session.execute(m_stmt)
        member = m_res.scalar_one_or_none()
        if not member:
            member = EquipoEjecutorMiembro(
                id=uuid.uuid4(),
                equipo_id=team1.id,
                usuario_id=user_map["apoyo.redes1@sena.edu.co"].id,
                activo=True,
            )
            session.add(member)

        # Team 2
        t2_stmt = select(EquipoEjecutor).where(EquipoEjecutor.nombre == "Equipo Redes 02")
        t2_res = await session.execute(t2_stmt)
        team2 = t2_res.scalar_one_or_none()
        if not team2:
            team2 = EquipoEjecutor(
                id=uuid.uuid4(),
                nombre="Equipo Redes 02",
                coordinacion_id=coordinacion.id,
                especialidad_id=especialidad.id,
                lider_id=user_map["lider.redes2@sena.edu.co"].id,
                estado=EstadoEquipo.ACTIVO,
            )
            session.add(team2)

        await session.commit()
        print("Seeding complete successfully! Demo users are ready for testing.")


if __name__ == "__main__":
    asyncio.run(seed())
