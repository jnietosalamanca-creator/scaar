"""Crea usuarios mínimos: system (para training) + un proyectista de prueba.

Uso:
    python -m app.scripts.seed_users
"""

import bcrypt
from sqlalchemy import select

from app.db.models import User
from app.db.session import SessionLocal


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

SEED = [
    {
        "email": "system@scaar.local",
        "nombre_completo": "Sistema SCAAR",
        "rol": "admin",
        "password": "system_change_me",
    },
    {
        "email": "proyectista@scaar.local",
        "nombre_completo": "Proyectista de Prueba",
        "rol": "proyectista",
        "cedula_prof": "0000000",
        "password": "proy_change_me",
    },
]


def main() -> None:
    with SessionLocal() as db:
        for u in SEED:
            existing = db.execute(
                select(User).where(User.email == u["email"])
            ).scalar_one_or_none()
            if existing:
                print(f"[seed_users] ya existe: {u['email']}")
                continue
            user = User(
                email=u["email"],
                nombre_completo=u["nombre_completo"],
                rol=u["rol"],
                cedula_prof=u.get("cedula_prof"),
                password_hash=hash_password(u["password"]),
            )
            db.add(user)
            print(f"[seed_users] creado: {u['email']} ({u['rol']})")
        db.commit()


if __name__ == "__main__":
    main()
