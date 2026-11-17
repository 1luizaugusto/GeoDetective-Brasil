"""Referência MapBiomas para cada par: % de vegetação NATIVA em cada ano, exatamente no
recorte do jogo, e Δ em pontos percentuais. Grava em metadata.json → reference_mapbiomas.

- 30 m Coleção 11 (1985–2025): referência principal.
- 10 m Coleção 4 (Sentinel-2): usada se o ano existir no asset (comparação de escala).
O cálculo amostra a 10 m na projeção UTM do par (nearest), ponderando por área.

Uso: python gee_reference_pairs.py --project <id>
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import gee  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def frac_native(asset_key, year, geom, crs):
    img = ee.Image(gee.ASSETS[asset_key])
    if f"classification_{year}" not in img.bandNames().getInfo():
        return None
    m = gee.native_mask(year, asset_key)
    v = m.reduceRegion(ee.Reducer.mean(), geom, scale=10, crs=crs, maxPixels=1e8).get("native").getInfo()
    return None if v is None else round(100 * v, 2)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--project"); a = ap.parse_args()
    gee.init(a.project)
    for mp in sorted((ROOT / "data" / "pairs").glob("*/metadata.json")):
        meta = json.loads(mp.read_text(encoding="utf-8"))
        geom, crs = gee.aoi_from_metadata(meta), meta["aoi"]["crs"]
        ya, yb = gee.pair_years(meta)
        ref = {"target": "vegetação nativa (Col. 11: " + ",".join(map(str, gee.NATIVE)) + ")",
               "computed_utc": datetime.now(timezone.utc).isoformat()}
        for key in ("lulc30_c11", "lulc10_c4"):
            pa, pb = frac_native(key, ya, geom, crs), frac_native(key, yb, geom, crs)
            ref[key] = {"asset": gee.ASSETS[key], f"native_pct_{ya}": pa, f"native_pct_{yb}": pb,
                        "delta_pp": None if pa is None or pb is None else round(pb - pa, 2)}
        meta["reference_mapbiomas"] = ref
        mp.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        print(meta["challenge_id"], json.dumps({k: v for k, v in ref.items() if k.startswith("lulc")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
