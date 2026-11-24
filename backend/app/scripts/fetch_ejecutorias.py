"""Descarga **ejecutorias de amparo** del Semanario Judicial de la Federación.

A diferencia de `fetch_sjf.py` (que baja TESIS — reglas abstractas), este
script baja **casos reales** (ejecutorias publicadas) para que el proyectista
los clasifique según la taxonomía de procedencia (8 categorías).

Endpoint público:
    GET /services/sjfejecutoriamicroservice/api/public/ejecutorias/{ius}

Cada ejecutoria es un JSON con:
    ius, rubro, tipoAsunto, instancia, sala, fechaPublicacion, texto (HTML), …

Heurística de extracción del **acto reclamado**:
  1. Filtrar `tipoAsunto` con "AMPARO" (excluye controversias / acciones).
  2. Limpiar HTML del campo `texto`.
  3. Anclar a la sección **"ANTECEDENTES"** (presente en todas las
     sentencias de SCJN/Tribunales que probé). Capturar 2,500 chars
     desde ese ancla — cubre "Demanda de amparo", "Hechos", autoridades
     responsables y descripción del acto reclamado.
  4. Si no hay ancla "ANTECEDENTES", caer a regex con frases típicas
     ("señaló como acto reclamado…", "reclamó la sentencia…").

Salida JSONL, una línea por caso, lista para POST /casos/import-ejecutorias.

Uso:
    python -m app.scripts.fetch_ejecutorias \\
        --ius-from 33500 --ius-to 33900 \\
        --out corpus/ejecutorias_pending.jsonl --max-casos 50
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://sjf2.scjn.gob.mx/services/sjfejecutoriamicroservice/api/public/ejecutorias"

# Solo tipos de asunto AMPARO. Excluye controversias constitucionales,
# acciones de inconstitucionalidad, contradicciones de criterios —
# eso es derecho procesal constitucional, no nuestro dominio.
AMPARO_RE = re.compile(r"^\s*AMPARO\b", re.IGNORECASE)

# Heurísticas para extraer el acto reclamado dentro de los primeros 25k chars.
PATRONES_ACTO = [
    # "señaló como actos reclamados la …"
    re.compile(r"(?i)se[ñn]al[óo]\s+como\s+actos?\s+reclamados?[^.]{20,800}\."),
    # "como acto reclamado el …"
    re.compile(r"(?i)como\s+actos?\s+reclamados?\s+(?:la|el|los|las)[^.]{20,800}\."),
    # "el acto reclamado consiste en …"
    re.compile(r"(?i)el\s+actos?\s+reclamados?\s+(?:consiste|es|fue|fueron)[^.]{20,800}\."),
    # "reclamó la sentencia / el laudo / la resolución …"
    re.compile(
        r"(?i)reclam[óa]\s+(?:la\s+sentencia|el\s+laudo|el\s+acuerdo|el\s+auto|"
        r"la\s+resoluci[óo]n)[^.]{0,800}\."
    ),
]


def clean_html(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"<\s*(br|/p)\s*/?\s*>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"&quot;", '"', s)
    s = re.sub(r"&#39;", "'", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def fetch_ejecutoria(ius: int, timeout: float = 30.0) -> dict | None:
    """GET ejecutoria por IUS. Devuelve None si 404."""
    req = urllib.request.Request(
        f"{BASE_URL}/{ius}",
        headers={
            "User-Agent": "SCAAR-Research/0.1 (legal AI corpus building)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def extraer_acto_reclamado(texto_limpio: str) -> tuple[str, str]:
    """Devuelve (acto_reclamado_candidato, metodo_extraccion).

    metodo_extraccion ∈ {'antecedentes', 'regex_acto', 'regex_reclamo', 'fallback_head'}
    para que la UI le diga al proyectista qué tanto confiar en el extract.
    """
    head = texto_limpio[:25000]

    # 1) Sección ANTECEDENTES — el ancla más fiable.
    m_ant = re.search(
        r"(?i)\bANTECEDENTES?\b(?:\s+Y\s+TR[ÁA]MITE)?(?:\s+DEL\s+JUICIO[^\n]*)?\b",
        head,
    )
    if m_ant:
        chunk = head[m_ant.start() : m_ant.start() + 2500].strip()
        # Cortar limpiamente en oración final si es posible.
        last_dot = chunk.rfind(".")
        if last_dot > 1500:
            chunk = chunk[: last_dot + 1]
        return chunk, "antecedentes"

    # 2) Regex de frases típicas.
    for pat in PATRONES_ACTO:
        m = pat.search(head)
        if m:
            return m.group().strip(), "regex_acto"

    # 3) Fallback: primeros 2000 chars del cuerpo.
    return head[:2000].strip(), "fallback_head"


def parse_fecha(raw: str | None) -> str | None:
    """SJF puede regresar 'YYYY-MM-DDTHH:MM:SS', 'YYYY-MM-DD HH:MM:SS.0', o
    'YYYY-MM-DD'. Tomamos los primeros 10 chars de la parte ISO."""
    if not raw:
        return None
    s = raw.replace("T", " ")[:10]
    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None


def to_caso_item(raw: dict) -> dict | None:
    """Convierte JSON de SJF en item listo para POST /casos/import-ejecutorias."""
    ius = raw.get("ius")
    tipo_asunto = raw.get("tipoAsunto") or ""
    if ius is None or not AMPARO_RE.search(tipo_asunto):
        return None

    texto_limpio = clean_html(raw.get("texto"))
    if len(texto_limpio) < 500:
        # Ejecutorias muy cortas no sirven — probablemente solo metadatos.
        return None

    rubro = clean_html(raw.get("rubro")) or tipo_asunto
    acto, metodo = extraer_acto_reclamado(texto_limpio)

    return {
        "registro_sjf": str(ius),
        "tipo_asunto": tipo_asunto.strip(),
        "rubro": rubro,
        "instancia": raw.get("instancia") or raw.get("sala") or "Desconocida",
        "promovente": raw.get("promovente") or None,
        "fecha_publ": parse_fecha(raw.get("fechaPublicacion")),
        "url_semanario": raw.get("urlSemanario") or None,
        "acto_reclamado_candidato": acto,
        "metodo_extraccion": metodo,
        # Texto completo en `descripcion_completa` — el endpoint de import lo
        # puede recortar o guardar entero según preferencia.
        "descripcion_completa": texto_limpio,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ius-from", type=int, required=True)
    ap.add_argument("--ius-to", type=int, required=True)
    ap.add_argument("--out", type=str, required=True)
    ap.add_argument(
        "--max-casos",
        type=int,
        default=200,
        help="Tope superior — se detiene al alcanzar este número de AMPAROs.",
    )
    ap.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Segundos entre requests (respeto al servidor SJF).",
    )
    ap.add_argument(
        "--descending",
        action="store_true",
        help="Iterar de ius-to hacia ius-from (casos más recientes primero).",
    )
    args = ap.parse_args()

    if args.ius_from >= args.ius_to:
        sys.exit("ius-from debe ser menor a ius-to")

    iterable = (
        range(args.ius_to - 1, args.ius_from - 1, -1)
        if args.descending
        else range(args.ius_from, args.ius_to)
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_total = n_404 = n_match = n_skip = n_err = 0
    by_metodo: dict[str, int] = {"antecedentes": 0, "regex_acto": 0, "fallback_head": 0}

    print(
        f"[fetch_ejecutorias] rango {args.ius_from}..{args.ius_to} "
        f"({'desc' if args.descending else 'asc'}), max={args.max_casos}",
        file=sys.stderr,
    )

    with out_path.open("w") as f:
        for ius in iterable:
            n_total += 1
            try:
                raw = fetch_ejecutoria(ius)
            except Exception as e:  # noqa: BLE001
                n_err += 1
                print(f"  ius={ius} error: {e}", file=sys.stderr)
                time.sleep(args.delay * 5)
                continue

            if raw is None:
                n_404 += 1
                continue

            item = to_caso_item(raw)
            if item is None:
                n_skip += 1
            else:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                n_match += 1
                by_metodo[item["metodo_extraccion"]] += 1
                print(
                    f"  ius={ius} ✓ [{item['metodo_extraccion'][:5]:5s}] "
                    f"{item['tipo_asunto'][:60]}",
                    file=sys.stderr,
                )
                if n_match >= args.max_casos:
                    print(
                        f"[fetch_ejecutorias] alcanzado --max-casos={args.max_casos}",
                        file=sys.stderr,
                    )
                    break

            if n_total % 25 == 0:
                print(
                    f"  progreso: {n_total} probados → {n_match} amparos, "
                    f"{n_404} 404s, {n_skip} no-amparo, {n_err} errores",
                    file=sys.stderr,
                )
            time.sleep(args.delay)

    print(
        f"\n[fetch_ejecutorias] DONE: total={n_total} amparos={n_match} "
        f"404={n_404} no-amparo={n_skip} err={n_err}",
        file=sys.stderr,
    )
    print(f"  Métodos de extracción: {by_metodo}", file=sys.stderr)
    print(f"  → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
