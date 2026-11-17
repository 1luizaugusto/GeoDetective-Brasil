"""Verifica a lista preliminar de localidades:
  - município/UF oficiais do ponto central (API de malhas do IBGE);
  - bioma oficial (IBGE, Biomas 1:250.000, 2019);
  - disponibilidade de Sentinel-2 L2A C1 (cenas que cobrem todo o recorte, nuvem do tile < 20%)
    na janela sazonal de 2020 e 2024.
Entrada:  data/catalog/candidates_v0.csv
Saída:    data/catalog/candidates_v0_verified.csv  (+ resumo no terminal)
NOTA: isto NÃO verifica se a mudança hipotética existe — isso exige triagem/QA visual por par.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pyogrio
from shapely import from_wkb
from shapely.geometry import Point
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import s2  # noqa: E402
from verify_pairs import locate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "catalog" / "candidates_v0.csv"
OUT = ROOT / "data" / "catalog" / "candidates_v0_verified.csv"
BIOMAS = ROOT / "data" / "external" / "ibge" / "biomas" / "lm_bioma_250.shp"


def load_biomes():
    meta, _, wkbs, field_data = pyogrio.raw.read(BIOMAS)  # (meta, fids, geometria WKB, atributos)
    names = dict(zip(meta["fields"], field_data))
    name_col = next(c for c in names if c.lower().startswith("bioma"))
    geoms = [from_wkb(g) for g in wkbs]
    return geoms, list(names[name_col]), meta.get("crs")


def main():
    geoms, bnames, crs = load_biomes()
    print("Biomas IBGE:", bnames, "CRS:", crs)
    tree = STRtree(geoms)
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    for r in rows:
        lon, lat = float(r["lon"]), float(r["lat"])
        p = Point(lon, lat)  # SIRGAS 2000 geográfico ~ WGS84 (diferença < 1 m)
        idx = [i for i in tree.query(p) if geoms[i].contains(p)]
        r["bioma_ibge"] = bnames[idx[0]] if idx else "(fora/limite)"
        loc = locate(lon, lat) or {}
        r["municipio_ibge"] = loc.get("municipio", "(não localizado)")
        r["uf_ibge"] = loc.get("uf", "")
        r["cod_ibge"] = loc.get("ibge_municipio_codigo", "")
        flags = []
        if r["uf_ibge"] != r["uf_esperada"]:
            flags.append("UF_DIVERGENTE")
        if r["bioma_ibge"].lower() != r["bioma_esperado"].lower():
            flags.append("BIOMA_DIVERGENTE")
        grid = s2.make_grid(lon, lat, float(r["recorte_km"]) * 1000, 10)
        a, b = r["janela_sazonal"].split("/")
        for y in (2020, 2024):
            ys, ye = (y, y + 1) if b < a else (y, y)  # janela que cruza o ano (ex.: dez-mar)
            try:
                its = s2.search(grid, f"{ys}-{a}", f"{ye}-{b}", max_tile_cloud=20)
                r[f"s2_cenas_{y}"] = len(its)
            except Exception as e:  # noqa: BLE001
                r[f"s2_cenas_{y}"] = f"erro {type(e).__name__}"
        if any(str(r[f"s2_cenas_{y}"]) == "0" for y in (2020, 2024)):
            flags.append("SEM_CENA_LIMPA")
        r["alertas"] = ";".join(flags)
        print(f'{r["id"]:7} {r["municipio_ibge"]}/{r["uf_ibge"]:2} | {r["bioma_ibge"]:15} | '
              f'S2 2020={r["s2_cenas_2020"]} 2024={r["s2_cenas_2024"]} | {r["alertas"]}')
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("->", OUT)


if __name__ == "__main__":
    main()
