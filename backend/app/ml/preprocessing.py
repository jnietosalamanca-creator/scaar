import hashlib
import re

from unidecode import unidecode


def normalize_text(text: str) -> str:
    """Normaliza para hashing y para alimentar TF-IDF.

    Mismas reglas en train y predict — si divergen, el sha256 del log no
    coincide entre re-clasificaciones del mismo acto.
    """
    text = unidecode(text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def acto_sha256(acto_reclamado: str) -> str:
    """SHA-256 hex del acto reclamado normalizado."""
    return hashlib.sha256(normalize_text(acto_reclamado).encode("utf-8")).hexdigest()
