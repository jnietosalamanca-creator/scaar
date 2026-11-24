import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.validate import ValidateRequest, ValidateResponse
from app.services.validator import ValidationError, validate_classification

router = APIRouter(prefix="/classifications", tags=["validate"])


@router.post(
    "/{classification_id}/validate",
    response_model=ValidateResponse,
    status_code=201,
)
def post_validate(
    classification_id: uuid.UUID,
    body: ValidateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ValidateResponse:
    try:
        record = validate_classification(
            db=db,
            classification_id=classification_id,
            user=user,
            veredicto=body.veredicto,
            clasificacion_corregida=body.clasificacion_corregida,
            comentario=body.comentario,
            supersedes_id=body.supersedes_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except IntegrityError as e:
        # Caso típico: supersedes_id ya fue superseded por otro veredicto
        # (UNIQUE constraint en classification_validations.supersedes_id).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"conflicto de integridad: {e.orig}",
        )

    return ValidateResponse(
        id=record.id,
        classification_id=record.classification_id,
        validated_by=record.validated_by,
        validated_at=record.validated_at,
        veredicto=record.veredicto,
        clasificacion_corregida=record.clasificacion_corregida,
        comentario=record.comentario,
        firma_sha256=record.firma_sha256,
        supersedes_id=record.supersedes_id,
    )
