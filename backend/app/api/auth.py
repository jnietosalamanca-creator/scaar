from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.execute(
        select(User).where(User.email == body.email, User.activo.is_(True))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        # Mensaje genérico — no filtrar si el email existe.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )
    token = create_access_token(
        subject=user.email,
        extra={"user_id": str(user.id), "rol": user.rol},
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_ttl_min * 60,
        user=MeResponse(
            id=user.id,
            email=user.email,
            nombre_completo=user.nombre_completo,
            rol=user.rol,  # type: ignore[arg-type]
        ),
    )


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(current_user)) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        nombre_completo=user.nombre_completo,
        rol=user.rol,  # type: ignore[arg-type]
    )
