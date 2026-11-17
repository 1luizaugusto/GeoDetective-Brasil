"""TRIAGEM de uma região candidata: encontra janelas de 5 km com maior perda/ganho/estabilidade.

ATENÇÃO: usa limiar simples de NDVI apenas para ESCOLHER recortes. Não é o resultado
científico do jogo (que virá do Random Forest + avaliação com MapBiomas).

Uso:
  python screen_region.py --name apui --lon -59.89 --lat -7.20 --size 24000 \
      --season 06-01 09-30 --years 2020 2024 --out ../../data/screening
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import pairing, render, s2  # noqa: E402

RES = 20.0
NDVI_T = 0.55


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--size", type=float, default=24000)
    ap.add_argument("--win", type=float, default=5000)
    ap.add_argument("--season", nargs=2, default=["06-01", "09-30"])
    ap.add_argument("--years", nargs=2, type=int, default=[2020, 2024])
    ap.add_argument("--out", default="data/screening")
    ap.add_argument("--metric", choices=["woody", "ndvi", "forest"], default="forest")
    ap.add_argument("--swir", type=float, default=0.16)
    ap.add_argument("--item-a"); ap.add_argument("--item-b")
    ap.add_argument("--ndvi", type=float, default=0.6)
    ap.add_argument("--ndmi", type=float, default=0.3)
    a = ap.parse_args()

    grid = s2.make_grid(a.lon, a.lat, a.size, RES)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.item_a and a.item_b:  # par fixado manualmente
        from pystac_client import Client
        col = Client.open(s2.EARTH_SEARCH).get_collection(s2.COLLECTION)
        ia_, ib_ = col.get_item(a.item_a), col.get_item(a.item_b)
        A = [(s2.scl_valid_fraction(ia_, grid)[0], ia_)]; B = [(s2.scl_valid_fraction(ib_, grid)[0], ib_)]
        pair = (A[0], B[0])
    else:
        pair, A, B = pairing.choose_pair(grid, a.years[0], a.years[1], tuple(a.season), valid_threshold=0.95)
    print(f"[{a.name}] candidatas {a.years[0]}:", [(round(f, 3), i.id) for f, i in A[:5]])
    print(f"[{a.name}] candidatas {a.years[1]}:", [(round(f, 3), i.id) for f, i in B[:5]])
    if not pair:
        print("  sem par disponível"); return
    (fa, ia), (fb, ib) = pair
    print(f"  par: {ia.id} ({fa:.3f})  x  {ib.id} ({fb:.3f})")

    data = []
    for it in (ia, ib):
        r = s2.read_reflectance(it, grid, ("red", "green", "blue", "nir", "swir16"))
        scl = s2._read(it.assets["scl"].href, grid, dtype="uint8")
        valid = np.isin(scl, s2.SCL_VALID) & np.isfinite(r["red"])
        ndvi = (r["nir"] - r["red"]) / (r["nir"] + r["red"] + 1e-6)
        ndmi = (r["nir"] - r["swir16"]) / (r["nir"] + r["swir16"] + 1e-6)
        # proxy de vegetação lenhosa/densa (triagem): verde E úmida no SWIR.
        # Pasto seco/verde tende a NDMI baixo; floresta/silvicultura, NDMI alto.
        if a.metric == "woody":
            veg = (ndvi > a.ndvi) & (ndmi > a.ndmi)
        elif a.metric == "forest":  # dossel fechado: escuro no SWIR (pasto, mesmo verde, é mais claro)
            veg = (ndvi > 0.7) & (r["swir16"] < a.swir)
        else:
            veg = ndvi > NDVI_T
        data.append((r, valid, veg))
    both = data[0][1] & data[1][1]
    v0 = data[0][2] & both
    v1 = data[1][2] & both

    w = int(a.win / RES); step = int(1000 / RES); n = grid.width
    rows = []
    for y in range(0, n - w + 1, step):
        for x in range(0, n - w + 1, step):
            m = both[y:y+w, x:x+w]
            if m.mean() < 0.97:
                continue
            p0 = v0[y:y+w, x:x+w].sum() / m.sum(); p1 = v1[y:y+w, x:x+w].sum() / m.sum()
            cx = grid.left + (x + w / 2) * RES; cy = grid.top - (y + w / 2) * RES
            from pyproj import Transformer
            lon, lat = Transformer.from_crs(grid.epsg, 4326, always_xy=True).transform(cx, cy)
            rows.append(dict(x=x, y=y, lon=round(lon, 5), lat=round(lat, 5),
                             veg_a=round(100 * p0, 1), veg_b=round(100 * p1, 1),
                             delta_pp=round(100 * (p1 - p0), 1), valid=round(float(m.mean()), 3)))
    if not rows:
        print("  nenhuma janela com cobertura válida suficiente"); return
    loss = sorted(rows, key=lambda r: r["delta_pp"])[:3]
    gain = sorted(rows, key=lambda r: -r["delta_pp"])[:3]
    stab = sorted([r for r in rows if r["veg_a"] > 60], key=lambda r: abs(r["delta_pp"]))[:3]
    res = dict(name=a.name, pair=[s2.item_summary(ia), s2.item_summary(ib)], valid=[fa, fb],
               metric=a.metric, ndvi_t=a.ndvi, ndmi_t=a.ndmi, loss=loss, gain=gain, stable=stab)
    (out / f"{a.name}_screen.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("loss", "gain", "stable"):
        print(f"  {k}:", [(r['lon'], r['lat'], r['veg_a'], r['veg_b'], r['delta_pp']) for r in res[k]])

    imgs = []
    for (r, valid, _), it in zip(data, (ia, ib)):
        im = Image.fromarray(render.to_rgb(r, render.TRUE_COLOR, render.STRETCH["true"]))
        d = ImageDraw.Draw(im)
        for col, lst in (((255, 60, 60), loss[:1]), ((60, 255, 60), gain[:1]), ((80, 160, 255), stab[:1])):
            for rr in lst:
                d.rectangle([rr["x"], rr["y"], rr["x"] + w, rr["y"] + w], outline=col, width=3)
        imgs.append(np.asarray(im))
    render.side_by_side(imgs[0], imgs[1], ia.id, ib.id,
                        f"Triagem {a.name} (vermelho=perda, verde=ganho, azul=estável; métrica={a.metric})",
                        out / f"{a.name}_screen.png")


if __name__ == "__main__":
    main()
