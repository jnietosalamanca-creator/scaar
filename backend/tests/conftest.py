"""Setup mínimo para pytest.

Lee el `.env` real del backend si existe (para tests de integración contra
la BD del usuario). Si no hay `.env`, cae a valores de prueba que dejan
los tests unitarios funcionar sin DB.
"""

import os
import sys
from pathlib import Path

# Permitir importar `app.*` sin instalación previa
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Si el .env existe, cargarlo ANTES de que pydantic-settings lo lea
ENV_FILE = ROOT / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        # No override de variables ya seteadas
        os.environ.setdefault(k, v)

# Fallbacks para tests unitarios que no necesitan DB real
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://scaar:scaar@localhost:5432/scaar_test"
)
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-not-for-prod" * 2)
os.environ.setdefault("VERDICT_HMAC_SECRET", "test-hmac-secret-not-for-prod" * 2)
