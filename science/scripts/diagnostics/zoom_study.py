"""Estudo de zoom: mesmo par, recortes menores ampliados por fator inteiro (Lanczos).
Lê o GeoTIFF 10 m já gerado do par e produz painéis lado a lado para avaliação visual.
Uso: python zoom_study.py data/pairs/PILOTO-01-PERDA out_dir"""
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from geodet import render  # noqa: E402

NAMES = ["blue", "green", "red", "rededge1", "rededge2", "rededge3", "nir", "nir08", "swir16", "swir22"]


def load(t):
    with rasterio.open(t) as s:
        a = s.read().astype("float32")
    a[a == -32768] = np.nan
    return {n: a[i] / 10000 for i, n in enumerate(NAMES)}


pair_dir, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
ta, tb = sorted(pair_dir.glob("*_refl10m.tif"))
A, B = load(ta), load(tb)
# centro do recorte = centro de massa da mudança (proxy floresta) — só para o estudo
fa = (A["nir"] - A["red"]) / (A["nir"] + A["red"]) > 0.7
fb = (B["nir"] - B["red"]) / (B["nir"] + B["red"]) > 0.7
ch = (fa & ~fb).astype(float)
ys, xs = np.nonzero(ch) if ch.sum() > 50 else (np.array([250]), np.array([250]))
cy, cx = int(np.median(ys)), int(np.median(xs))
for size_px, factor in [(500, 1), (300, 2), (250, 2), (200, 3), (150, 4)]:
    h = size_px // 2
    y0 = min(max(cy - h, 0), 500 - size_px); x0 = min(max(cx - h, 0), 500 - size_px)
    sl = (slice(y0, y0 + size_px), slice(x0, x0 + size_px))
    a = {k: v[sl] for k, v in A.items()}; b = {k: v[sl] for k, v in B.items()}
    tone = render.pair_tone(a, b)
    ia = render.upscale(render.apply_tone(a, tone), factor)
    ib = render.upscale(render.apply_tone(b, tone), factor)
    km = size_px * 10 / 1000
    render.side_by_side(ia, ib, ta.stem[-18:-8], tb.stem[-18:-8],
                        f"{km:g} km × {km:g} km  ({size_px} px nativos ×{factor} → {size_px*factor} px na tela)",
                        out / f"zoom_{size_px}px_x{factor}.png", scale_px=int(50 * factor), scale_m=500)
    print("ok", size_px, factor)
