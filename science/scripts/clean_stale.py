"""Remove de data/pairs/<ID>/ arquivos de datas que NÃO são as do metadata.json atual
(sobras de reconstruções anteriores). Lista o que removeu. Uso: python clean_stale.py [--dry]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
dry = "--dry" in sys.argv
for mp in sorted((ROOT / "data" / "pairs").glob("*/metadata.json")):
    m = json.loads(mp.read_text(encoding="utf-8"))
    dates = {im["datetime_utc"][:10] for im in m["images"]}
    for f in mp.parent.iterdir():
        stem = f.name
        d = None
        for pre in ("game_", "context_"):
            if stem.startswith(pre):
                d = stem[len(pre):len(pre) + 10]
        if stem.endswith(("_refl10m.tif", "_scl10m.tif")):
            d = stem.split("_")[-2]
        if d and d not in dates:
            print(("[dry] " if dry else "") + "remove", f.relative_to(ROOT))
            if not dry:
                f.unlink()
