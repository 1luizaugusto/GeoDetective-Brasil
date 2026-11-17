"""Prévia RGB das melhores datas para o RECORTE de 2,4 km de um desafio (para QA visual de nuvem pequena).
Triagem pelo CDSE no recorte exato (SCL válido ≥ min-valid e névoa ≤ haze-max), depois renderiza
as N melhores de cada ano numa folha data/qa/preview_<ID>.png com os IDs Earth Search.
Uso: python preview_dates.py <ID> [--years 2020 2025] [--n 6] [--season MM-DD MM-DD] [--haze-max 0.03]
Escolhidas as cenas, fixe-as no catálogo com item_a / item_b."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import cdse, s2  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("id"); ap.add_argument("--years", nargs="+", type=int, default=[2020, 2025])
ap.add_argument("--n", type=int, default=6); ap.add_argument("--season", nargs=2, default=["01-01", "12-31"])
ap.add_argument("--min-valid", type=float, default=0.995); ap.add_argument("--haze-max", type=float, default=0.03)
a = ap.parse_args()

m = json.loads((ROOT / "data" / "pairs" / a.id / "metadata.json").read_text(encoding="utf-8"))
l, b, r, t = m["aoi"]["bounds_utm"]; h, w = m["aoi"]["shape"]
G = s2.Grid(int(m["aoi"]["crs"].split(":")[1]), l, t, w, h, 10.0)
T = 300
rows = []
for y in a.years:
    st = cdse.screen_dates(G, f"{y}-{a.season[0]}", f"{y}-{a.season[1]}", res=20)
    ok = sorted([s for s in st if s["valid"] >= a.min_valid and s["haze"] <= a.haze_max], key=lambda s: (-s["valid"], s["haze"]))
    tiles = []
    for s in ok[: a.n]:
        its = s2.search(G, s["date"], s["date"], max_tile_cloud=100)
        if not its:
            continue
        rf = s2.read_reflectance(its[0], G, ("red", "green", "blue"))
        rgb = np.clip(np.nan_to_num(np.dstack([rf[k] for k in ("red", "green", "blue")])) / 0.18, 0, 1) ** 0.8
        im = Image.fromarray((rgb * 255).astype("uint8")).resize((T, T))
        ImageDraw.Draw(im).text((4, 4), f"{s['date']} v={s['valid']:.3f} hz={s['haze']:.3f}", fill=(255, 255, 0))
        tiles.append(im)
        print(y, s["date"], its[0].id, round(s["valid"], 4), round(s["haze"], 3))
    rows.append(tiles)
W = max(len(r) for r in rows) if rows else 1
sheet = Image.new("RGB", (max(W, 1) * (T + 6), len(rows) * (T + 6)), (16, 20, 28))
for i, tiles in enumerate(rows):
    for j, im in enumerate(tiles):
        sheet.paste(im, (j * (T + 6), i * (T + 6)))
out = ROOT / "data" / "qa" / f"preview_{a.id}.png"
out.parent.mkdir(parents=True, exist_ok=True); sheet.save(out); print(out)
