"""PRIMEIRO script a rodar após autenticar no GEE.
Confere se cada asset do MapBiomas abre, lista as bandas/anos disponíveis e mostra o
histograma de classes dentro do recorte de cada par-piloto (sanidade da legenda).

Uso: python gee_inspect_assets.py --project <seu-projeto-gcp>
Saída: data/catalog/gee_assets_inspection.json
"""
import argparse
import json
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import gee  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--project"); a = ap.parse_args()
    gee.init(a.project)
    report = {"assets": {}, "pilots": {}}
    for key, aid in gee.ASSETS.items():
        try:
            img = ee.Image(aid)
            bands = img.bandNames().getInfo()
            report["assets"][key] = {"id": aid, "ok": True, "n_bands": len(bands),
                                     "first": bands[:3], "last": bands[-3:]}
            print(f"OK   {key}: {len(bands)} bandas  {bands[:2]} … {bands[-2:]}")
        except Exception as e:  # noqa: BLE001
            report["assets"][key] = {"id": aid, "ok": False, "error": str(e)[:300]}
            print(f"FALHA {key}: {str(e)[:200]}")

    for mp in sorted((ROOT / "data" / "pairs").glob("*/metadata.json")):
        meta = json.loads(mp.read_text(encoding="utf-8"))
        geom = gee.aoi_from_metadata(meta)
        out = {}
        for key in ("lulc30_c11", "lulc10_c4", "defor_secveg_c11"):
            if not report["assets"].get(key, {}).get("ok"):
                continue
            img = ee.Image(gee.ASSETS[key]); bands = img.bandNames().getInfo()
            for y in gee.pair_years(meta):
                b = f"classification_{y}"
                if b not in bands:
                    out[f"{key}_{y}"] = "ano indisponível"; continue
                h = img.select(b).reduceRegion(ee.Reducer.frequencyHistogram(), geom,
                                               scale=10, crs=meta["aoi"]["crs"], maxPixels=1e8).getInfo()
                out[f"{key}_{y}"] = h.get(b)
        report["pilots"][meta["challenge_id"]] = out
        print(meta["challenge_id"], json.dumps(out)[:400])
    dst = ROOT / "data" / "catalog" / "gee_assets_inspection.json"
    dst.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("->", dst)


if __name__ == "__main__":
    main()
