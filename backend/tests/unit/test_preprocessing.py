"""Tests del preprocesamiento — la base del SHA del acto y de TF-IDF.

`acto_sha256` debe ser:
  • Determinístico (mismo texto → mismo hash).
  • Insensible a ruido cosmético (mayúsculas, acentos, espacios).
  • Sensible a cambios sustantivos (cualquier cambio de palabra).

Si esto se rompe, el log inmutable pierde su capacidad de detectar
re-clasificaciones del mismo acto.
"""

from app.ml.preprocessing import acto_sha256, normalize_text


def test_normalize_minusculas_y_sin_acentos():
    assert normalize_text("ACTO RECLAMADO Áéíóú Ñ") == "acto reclamado aeiou n"


def test_normalize_colapsa_espacios():
    assert (
        normalize_text("hola    mundo  \n\n  prueba")
        == "hola mundo prueba"
    )


def test_normalize_strip():
    assert normalize_text("   con espacios al inicio y al final   ") == (
        "con espacios al inicio y al final"
    )


def test_sha256_determinístico():
    a = "El juez negó la admisión de la prueba pericial."
    assert acto_sha256(a) == acto_sha256(a)


def test_sha256_robusto_a_mayusculas():
    """Un acto en mayúsculas y minúsculas debe producir el MISMO hash —
    así el sistema detecta duplicados aunque el proyectista pegue con
    formato distinto."""
    a = "Se decretó embargo precautorio."
    b = "SE DECRETÓ EMBARGO PRECAUTORIO."
    assert acto_sha256(a) == acto_sha256(b)


def test_sha256_robusto_a_acentos():
    a = "negó admisión pericial"
    b = "nego admision pericial"
    assert acto_sha256(a) == acto_sha256(b)


def test_sha256_sensible_a_cambio_sustantivo():
    """Un cambio de palabra clave SÍ debe cambiar el hash."""
    a = "El juez negó la admisión de la prueba pericial."
    b = "El juez admitió la prueba pericial."
    assert acto_sha256(a) != acto_sha256(b)


def test_sha256_es_64_hex():
    h = acto_sha256("texto cualquiera")
    assert len(h) == 64
    int(h, 16)  # parsea como hex
