"""Carga corpus desde JSONL hacia la tabla `tesis`. Idempotente por registro_sjf.

Uso:
    python -m app.scripts.seed_corpus
    python -m app.scripts.seed_corpus --path corpus/tesis_real.jsonl
"""

import argparse
import datetime as dt
import json
from pathlib import Path

from sqlalchemy import select

from app.db.models import Tesis
from app.db.session import SessionLocal


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="corpus/tesis_dummy.jsonl")
    args = ap.parse_args()
    src = Path(args.path)
    if not src.exists():
        raise SystemExit(f"No existe el archivo: {src}")

    inserted = skipped = 0
    with SessionLocal() as db, src.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            existing = db.execute(
                select(Tesis).where(Tesis.registro_sjf == row["registro_sjf"])
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue
            fecha = row.get("fecha_publ")
            tesis = Tesis(
                registro_sjf=row["registro_sjf"],
                epoca=row["epoca"],
                instancia=row["instancia"],
                tipo=row["tipo"],
                rubro=row["rubro"],
                texto=row["texto"],
                etiqueta=row["etiqueta"],
                fecha_publ=dt.date.fromisoformat(fecha) if fecha else None,
            )
            db.add(tesis)
            inserted += 1
        db.commit()
    print(f"[seed_corpus] insertadas={inserted} ya_existían={skipped}")


if __name__ == "__main__":
    main()
