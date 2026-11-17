"""Gera todos os pares definidos num catálogo JSON (ex.: data/catalog/pilots.json, challenges_v1.json).
Uso: python build_from_catalog.py <catalogo.json> [--only ID] [--skip-done]
Erros por item são registrados em data/catalog/build_log.jsonl e não interrompem o lote."""
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_pair  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "data" / "catalog" / "build_log.jsonl"
args = sys.argv[1:]
cat = json.loads(Path(args[0]).read_text(encoding="utf-8"))
only = args[args.index("--only") + 1] if "--only" in args else None
skip_done = "--skip-done" in args

for c in cat:
    if only and c["id"] != only:
        continue
    if skip_done and (ROOT / "data" / "pairs" / c["id"] / "metadata.json").exists():
        continue
    argv = ["--id", c["id"], "--name", c["name"], "--lon", str(c["lon"]), "--lat", str(c["lat"]),
            "--mode", c.get("mode", c.get("crop_mode", "stable_edge")),
            "--hypothesis", c.get("hypothesis", ""), "--notes", c.get("notes", ""),
            "--group", c.get("group", ""), "--biome", c.get("biome", "")]
    if "years" in c:
        argv += ["--years", *map(str, c["years"])]
    if "season" in c:
        argv += ["--season", *c["season"]]
    if c.get("item_a") and c.get("item_b"):
        argv += ["--item-a", c["item_a"], "--item-b", c["item_b"]]
    if c.get("exclude"):
        argv += ["--exclude", *c["exclude"]]
    for k in ("search", "crop", "zoom", "min_valid", "max_eval", "haze_max"):
        if k in c:
            argv += [f"--{k.replace('_', '-')}", str(c[k])]
    rec = {"id": c["id"], "utc": datetime.now(timezone.utc).isoformat()}
    try:
        m = build_pair.main(argv)
        rec.update(ok=True, delta_10m=m["reference_mapbiomas"]["delta_pp_10m"],
                   delta_30m=m["reference_mapbiomas"]["delta_pp_30m"], flags=m["qa"]["auto_flags"])
    except SystemExit as e:
        rec.update(ok=False, error=str(e)); print("  FALHOU:", e)
    except Exception as e:  # noqa: BLE001
        rec.update(ok=False, error=repr(e)[:300]); traceback.print_exc()
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
