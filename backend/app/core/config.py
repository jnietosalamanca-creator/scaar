from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_log_level: str = "INFO"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_min: int = 60

    verdict_hmac_secret: str
    verdict_hmac_key_version: str = "v1"

    ml_artifacts_dir: str = "/app/app/ml/artifacts"
    ml_active_model_version: str | None = None

    # Zona de revisión humana obligatoria. Si la probabilidad cae en
    # [classify_review_lower, classify_review_upper] el endpoint marca
    # requiere_revision_humana=True. La predicción aún se devuelve y se
    # persiste — la decisión es del proyectista, no del modelo.
    classify_review_lower: float = 0.30
    classify_review_upper: float = 0.70

    # Fuentes excluidas del training. El dummy v1 quedó obsoleto cuando se
    # asentó la doctrina IV.2o.C. J/2 — sus etiquetas reflejan el criterio
    # derogado de "grado predominante o superior".
    # Coma-separadas en .env, ej: "dummy_v1_obsoleto,otra_fuente_mala".
    excluded_fuentes_train: str = "dummy_v1_obsoleto"

    # Mínimo de tesis adj+sus de fuentes confiables para que el reentreno
    # produzca un modelo "limpio" (recomendación operativa, no constraint).
    train_clean_threshold: int = 30

    @property
    def excluded_fuentes_list(self) -> list[str]:
        return [f.strip() for f in self.excluded_fuentes_train.split(",") if f.strip()]


settings = Settings()
