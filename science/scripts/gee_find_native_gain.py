"""Procura recortes de 2,4 km com GANHO de vegetação NATIVA segundo o MapBiomas Col. 11,
para depois buscar o par Sentinel-2 correspondente (screen_region.py / build_pair.py).

Critério por pixel (30 m), conservador para evitar ruído de classificação e plantio:
  - NÃO nativo em 2019 E em 2020   (uso antrópico consolidado antes do início)
  - nativo em 2024 E em 2025       (regeneração persistente, não oscilação de um ano)
  - não silvicultura em nenhum desses anos
Opcional (--exclude-fire): descarta pixels queimados em 2019–2020 (MapBiomas Fogo 5.1),
para separar regeneração de simples rebrota pós-fogo. Se o asset de fogo tiver bandas
com outro nome, o script avisa e segue sem esse filtro.

Agrega a fração de pixels que ganharam (e que perderam) numa grade de ~2,4 km e lista
as melhores células. Saída: data/catalog/native_gain_candidates.csv

Uso:
  python gee_find_native_gain.py --project <id> --bbox -50 -25 -44 -21 --top 15 --label mata_atlantica_sp
"""
import argparse
import csv
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import gee  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def is_native(cls):
    return cls.remap(gee.NATIVE, [1] * len(gee.NATIVE), 0)


def is_silv(cls):
    return cls.remap(gee.SILVICULTURE, [1], 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("W", "S", "E", "N"))
    ap.add_argument("--label", default="regiao")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--cell-m", type=float, default=2400)
    ap.add_argument("--exclude-fire", action="store_true")
    a = ap.parse_args()
    gee.init(a.project)

    lulc = ee.Image(gee.ASSETS["lulc30_c11"])
    c = {y: lulc.select(f"classification_{y}") for y in (2019, 2020, 2024, 2025)}
    gain = (is_native(c[2019]).Not().And(is_native(c[2020]).Not())
            .And(is_native(c[2024])).And(is_native(c[2025])))
    loss = (is_native(c[2019]).And(is_native(c[2020]))
            .And(is_native(c[2024]).Not()).And(is_native(c[2025]).Not()))
    silv = is_silv(c[2019]).Or(is_silv(c[2020])).Or(is_silv(c[2024])).Or(is_silv(c[2025]))
    gain = gain.And(silv.Not())
    native20 = is_native(c[2020])

    if a.exclude_fire:
        fire = ee.Image(gee.ASSETS["fire_annual_c51"])
        names = fire.bandNames().getInfo()
        fb = [n for n in names if n.endswith("2019") or n.endswith("2020")]
        if fb:
            burned = fire.select(fb).unmask(0).gt(0).reduce(ee.Reducer.max())
            gain = gain.And(burned.Not())
            print("filtro de fogo aplicado com bandas:", fb)
        else:
            print("AVISO: bandas de 2019/2020 não encontradas no asset de fogo:", names[:5], "… filtro ignorado")

    stack = (ee.Image.cat([gain.rename("gain"), loss.rename("loss"), native20.rename("native2020")])
             .unmask(0).toFloat())
    region = ee.Geometry.Rectangle(a.bbox)
    proj = ee.Projection("EPSG:4326").atScale(a.cell_m)
    cells = (stack.reduceResolution(ee.Reducer.mean(), maxPixels=65535)
             .reproject(proj)
             .addBands(ee.Image.pixelLonLat()))
    # Amostra todas as células da região e ordena no cliente
    fc = cells.sample(region=region, projection=proj, geometries=False, dropNulls=True)
    rows = fc.sort("gain", False).limit(a.top).getInfo()["features"]
    out = ROOT / "data" / "catalog" / "native_gain_candidates.csv"
    new = not out.exists()
    with out.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["regiao", "lon", "lat", "ganho_nativo_pct_celula", "perda_nativa_pct_celula",
                        "nativa_2020_pct", "criterio", "fonte"])
        for ft in rows:
            p = ft["properties"]
            w.writerow([a.label, round(p["longitude"], 5), round(p["latitude"], 5),
                        round(100 * p["gain"], 1), round(100 * p["loss"], 1), round(100 * p["native2020"], 1),
                        "não-nativo 2019-20 → nativo 2024-25, sem silvicultura" + (", sem fogo 2019-20" if a.exclude_fire else ""),
                        gee.ASSETS["lulc30_c11"]])
            print(f'{p["longitude"]:.5f} {p["latitude"]:.5f}  ganho={100*p["gain"]:.1f}%  perda={100*p["loss"]:.1f}%')
    print("->", out, "(candidatos MapBiomas; ainda exigem par Sentinel-2 + QA visual)")


if __name__ == "__main__":
    main()
