"""Exporta rótulos MapBiomas por recorte (grade idêntica ao GeoTIFF Sentinel-2 do desafio).
Saída: data/pairs/<ID>/<ID>_labels10m.tif, bandas uint8:
  n10_a, n10_b  nativa (1) / não-nativa (0) — MapBiomas 10 m Col.4   ← RÓTULO de treino do RF
  n30_a, n30_b  nativa — MapBiomas 30 m Col.11 (referência independente, reamostrada nearest)
  s30_a, s30_b  silvicultura — Col.11
Uso: python export_labels.py [--only ID] [--force]"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_pair import save_tif  # noqa: E402
from geodet import gee  # noqa: E402
from geodet.s2 import Grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("--only"); ap.add_argument("--force", action="store_true")
ap.add_argument("--skip", nargs="*", default=[], help="IDs a ignorar (ex.: em reconstrução)")
ap.add_argument("--project", default="geodetective-brasil")
a = ap.parse_args()
gee.init(a.project)
for mp in sorted((ROOT / "data" / "pairs").glob("*/metadata.json")):
    m = json.loads(mp.read_text(encoding="utf-8"))
    cid = m["challenge_id"]
    if (a.only and cid != a.only) or cid in a.skip:
        continue
    out = mp.parent / f"{cid}_labels10m.tif"
    refl = list(mp.parent.glob("*_refl10m.tif"))  # metadata.json é reescrito pelo train_rf; o GeoTIFF não
    newest = max((p.stat().st_mtime for p in refl), default=0)
    if out.exists() and not a.force and out.stat().st_mtime >= newest:  # rótulo mais novo que o par
        continue
    l, b, r, t = m["aoi"]["bounds_utm"]
    h, w = m["aoi"]["shape"]
    g = Grid(int(m["aoi"]["crs"].split(":")[1]), l, t, w, h, 10.0)
    ya, yb = gee.pair_years(m)
    arr = gee.masks_on_grid(g, ya, yb)
    names = ["n10_a", "n10_b", "n30_a", "n30_b", "s30_a", "s30_b"]
    save_tif(out, [arr[n] for n in names], g, "uint8", 255, names,
             {"years": f"{ya},{yb}", "source": "MapBiomas Col.4 10m / Col.11 30m via GEE"})
    print(cid, ya, yb, {n: round(float(arr[n].mean()) * 100, 1) for n in names[:2]})
