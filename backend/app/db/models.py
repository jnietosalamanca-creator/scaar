from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str] = mapped_column(String, nullable=False)
    cedula_prof: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("rol IN ('proyectista','socio','admin')", name="users_rol_check"),
    )


class Tesis(Base):
    __tablename__ = "tesis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registro_sjf: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    epoca: Mapped[str] = mapped_column(Text, nullable=False)
    instancia: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    rubro: Mapped[str] = mapped_column(Text, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    # Nullable: las tesis recién importadas están "pendientes" hasta que
    # un proyectista las etiquete vía /tesis/{id}/label.
    etiqueta: Mapped[str | None] = mapped_column(String)
    fecha_publ: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    etiquetada_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    etiquetada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fuente: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    # Doctrina canónica = tesis que define el criterio jurídico aplicable
    # (ej. IV.2o.C. J/2). NO se entrena con ellas, NO aparecen en flujo de
    # etiquetado pendiente, pero SE muestran como criterio en la UI.
    es_doctrina_canonica: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Rol jurisprudencial — solo `regla` entra al training. Excepciones,
    # tesis aisladas dudosas y derogadas se preservan en el corpus pero NO
    # contaminan el aprendizaje del modelo (evita señal contradictoria).
    tipo_jurisprudencial: Mapped[str] = mapped_column(
        Text, nullable=False, default="regla"
    )
    notas_metodologicas: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("tipo IN ('jurisprudencia','aislada')", name="tesis_tipo_check"),
        CheckConstraint(
            "etiqueta IS NULL OR etiqueta IN ('adjetivo','sustantivo','no_aplica')",
            name="tesis_etiqueta_check",
        ),
        Index("idx_tesis_etiqueta", "etiqueta"),
        Index("idx_tesis_fuente", "fuente"),
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    algoritmo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_corte: Mapped[date] = mapped_column(Date, nullable=False)
    n_tesis_train: Mapped[int] = mapped_column(Integer, nullable=False)
    metricas: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    activo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )


class Caso(Base):
    """Expediente del despacho — agrupación de actos reclamados.

    Mutable (sí permite UPDATE) — la mutabilidad del caso no afecta la
    inmutabilidad de los logs de cada `Classification` asociada.
    """

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identificador: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    materia: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Classification(Base):
    """Append-only. Trigger DB bloquea UPDATE/DELETE — el log es evidencia."""

    __tablename__ = "classifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acto_reclamado: Mapped[str] = mapped_column(Text, nullable=False)
    acto_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False
    )
    # Asociación opcional al expediente del despacho.
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id")
    )
    prediccion: Mapped[str] = mapped_column(String, nullable=False)
    # Legacy: solo se llena cuando la categoría predicha equivale al binario
    # de los modelos viejos (en_juicio_imposible/diferida). Nullable desde v0.3.
    prob_adjetivo: Mapped[float | None] = mapped_column(Numeric(6, 5))
    # Multiclase v0.3+: probabilidad de la categoría dominante.
    prob_categoria: Mapped[float | None] = mapped_column(Numeric(6, 5))
    # Distribución completa de probabilidades por clase del modelo activo.
    prob_por_clase: Mapped[dict[str, float] | None] = mapped_column(JSONB)
    top_features: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    top_analogas: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        # Constraint manejada en migration 005 (acepta 8 categorías + legacy).
        Index("idx_class_sha", "acto_sha256"),
        Index("idx_class_user_date", "created_by", "created_at"),
    )


class ClassificationValidation(Base):
    """Append-only con cadena de supersede. Triggers DB protegen veredicto/firma."""

    __tablename__ = "classification_validations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classifications.id"), nullable=False
    )
    validated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    validated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    veredicto: Mapped[str] = mapped_column(String, nullable=False)
    clasificacion_corregida: Mapped[str | None] = mapped_column(String)
    comentario: Mapped[str | None] = mapped_column(Text)

    aprobado_para_corpus: Mapped[bool] = mapped_column(default=False, nullable=False)
    aprobado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    aprobado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    firma_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    firma_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classification_validations.id"), unique=True
    )

    __table_args__ = (
        CheckConstraint(
            "veredicto IN ('acepta','rechaza')",
            name="val_veredicto_check",
        ),
        CheckConstraint(
            "clasificacion_corregida IS NULL OR clasificacion_corregida IN ('adjetivo','sustantivo')",
            name="val_corregida_check",
        ),
    )
