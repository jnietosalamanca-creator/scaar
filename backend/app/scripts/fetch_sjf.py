"""Descarga tesis del Semanario Judicial de la Federación (SJF) por rango de IUS.

Cada tesis tiene un IUS (registro digital). El endpoint público
GET /services/sjftesismicroservice/api/public/tesis/{ius}
devuelve un JSON con rubro, texto, época, instancia, etc.

Estrategia:
  1. Iterar IUS en un rango.
  2. Filtrar localmente por keywords del dominio (texto + rubro).
  3. Emitir un JSONL listo para POST /tesis/import.

Uso:
    python -m app.scripts.fetch_sjf --ius-from 2031000 --ius-to 2032000 \\
        --out corpus/sjf_pending.jsonl

    python -m app.scripts.fetch_sjf --ius-from 2031000 --ius-to 2031200 \\
        --keywords "imposible reparación,amparo indirecto,violación procesal" \\
        --out corpus/sjf_pending.jsonl --max-tesis 100
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

BASE_URL = "https://sjf2.scjn.gob.mx/services/sjftesismicroservice/api/public/tesis"

DEFAULT_KEYWORDS = [
    "imposible reparación",
    "imposible reparacion",
    "amparo indirecto",
    "amparo directo",
    "violación procesal",
    "violacion procesal",
    "violaciones procesales",
    "leyes del procedimiento",
    "afecta las defensas",
    "trasciende al resultado",
    "diferid",  # diferida, diferido, diferidamente
]


def clean_html(s: str | None) -> str:
    if not s:
        return ""
    # Reemplaza <br>, <p> por saltos
    s = re.sub(r"<\s*(br|/p)\s*/?\s*>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"&quot;", '"', s)
    s = re.sub(r"&#39;", "'", s)
    s = re.sub(r"\s+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


EPOCA_MAP = {
    "Quinta Época": "Quinta",
    "Sexta Época": "Sexta",
    "Séptima Época": "Séptima",
    "Octava Época": "Octava",
    "Novena Época": "Novena",
    "Décima Época": "Décima",
    "Undécima Época": "Undécima",
    "Duodécima Época": "Duodécima",
}


def normalize_epoca(s: str | None) -> str:
    if not s:
        return "Desconocida"
    return EPOCA_MAP.get(s.strip(), s.strip())


def normalize_tipo(raw: dict) -> str:
    """Map del campo 'tipoTesis' o 'ta_tj' al enum del schema (jurisprudencia/aislada)."""
    t = (raw.get("tipoTesis") or "").lower()
    if "jurisp" in t:
        return "jurisprudencia"
    if "aislad" in t:
        return "aislada"
    # Fallback con ta_tj: 1 = jurisprudencia (parece), 0 = aislada
    if raw.get("ta_tj") == 1:
        return "jurisprudencia"
    return "aislada"


def matches_keywords(rubro: str, texto: str, keywords: list[str]) -> bool:
    haystack = (rubro + " " + texto).lower()
    return any(k.lower() in haystack for k in keywords)


def fetch_tesis(ius: int, timeout: float = 15.0) -> dict | None:
    req = urllib.request.Request(
        f"{BASE_URL}/{ius}",
        headers={
            "User-Agent": "SCAAR-Research/0.1 (corpus building for legal AI tool)",
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


def to_corpus_item(raw: dict) -> dict | None:
    ius = raw.get("ius")
    if ius is None:
        return None
    rubro = clean_html(raw.get("rubro"))
    texto = clean_html(raw.get("texto"))
    if not rubro or len(texto) < 30:
        return None
    fecha_publ_raw = raw.get("fechaPublicacion")
    # SJF puede regresar "2025-11-14T10:25:00Z", "2025-11-14 10:25:00.0" o solo
    # "2025-11-14". Tomamos los primeros 10 chars de la parte ISO.
    if fecha_publ_raw:
        s = fecha_publ_raw.replace("T", " ")[:10]
        fecha_publ = s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None
    else:
        fecha_publ = None
    return {
        "registro_sjf": str(ius),
        "epoca": normalize_epoca(raw.get("epoca")),
        "instancia": raw.get("instancia") or raw.get("sala") or "Desconocida",
        "tipo": normalize_tipo(raw),
        "rubro": rubro,
        "texto": texto,
        "fecha_publ": fecha_publ,
        # etiqueta queda fuera — lo decide el proyectista vía /tesis/{id}/label
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ius-from", type=int, required=True)
    ap.add_argument("--ius-to", type=int, required=True)
    ap.add_argument(
        "--keywords",
        type=str,
        default=",".join(DEFAULT_KEYWORDS),
        help="Coma-separadas. Una tesis pasa si su rubro+texto contiene CUALQUIERA.",
    )
    ap.add_argument("--out", type=str, required=True)
    ap.add_argument("--max-tesis", type=int, default=10000)
    ap.add_argument("--delay", type=float, default=0.2, help="Segundos entre requests.")
    args = ap.parse_args()

    if args.ius_from >= args.ius_to:
        sys.exit("ius-from debe ser menor a ius-to")

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    print(f"[fetch_sjf] rango {args.ius_from}..{args.ius_to}", file=sys.stderr)
    print(f"[fetch_sjf] keywords: {keywords}", file=sys.stderr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_total = n_404 = n_match = n_skip = n_err = 0
    with out_path.open("w") as f:
        for ius in range(args.ius_from, args.ius_to):
            n_total += 1
            try:
                raw = fetch_tesis(ius)
            except Exception as e:  # noqa: BLE001
                n_err += 1
                print(f"  ius={ius} error: {e}", file=sys.stderr)
                time.sleep(args.delay * 5)
                continue
            if raw is None:
                n_404 += 1
                continue
            item = to_corpus_item(raw)
            if item is None:
                n_skip += 1
            elif matches_keywords(item["rubro"], item["texto"], keywords):
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                n_match += 1
                print(
                    f"  ius={ius} ✓ {item['rubro'][:80]}",
                    file=sys.stderr,
                )
                if n_match >= args.max_tesis:
                    print(
                        f"[fetch_sjf] alcanzado --max-tesis={args.max_tesis}",
                        file=sys.stderr,
                    )
                    break
            else:
                n_skip += 1
            if n_total % 20 == 0:
                print(
                    f"  progreso: {n_total} probadas, {n_match} matches, "
                    f"{n_404} 404s, {n_skip} sin keyword, {n_err} errores",
                    file=sys.stderr,
                )
            time.sleep(args.delay)

    print(
        f"[fetch_sjf] DONE: total={n_total} match={n_match} 404={n_404} "
        f"sin_kw={n_skip} err={n_err} → {out_path}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
