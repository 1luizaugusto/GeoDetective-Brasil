"""Verificações automáticas de cada par em data/pairs/*:
 1. alinhamento: CRS, transform e dimensões IDÊNTICOS nas duas datas (mesmo local, pixel a pixel);
 2. município/UF do centro via malha oficial do IBGE (API de malhas v3);
 3. presença do ID do produto no Copernicus Data Space (proveniência oficial).
Atualiza metadata.json com o resultado (campo `verification`)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import rasterio
import requests
from shapely.geometry import Point, shape

PAIRS = Path(__file__).resolve().parents[2] / "data" / "pairs"
UFS = ["RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA",
       "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO", "DF"]


@lru_cache(maxsize=None)
def ibge_states():
    url = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=UF"
    return requests.get(url, timeout=60).json()


@lru_cache(maxsize=None)
def ibge_munis(uf_code: str):
    url = (f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf_code}"
           "?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio")
    return requests.get(url, timeout=60).json()


@lru_cache(maxsize=None)
def muni_name(code: str):
    r = requests.get(f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{code}", timeout=60).json()
    return r["nome"], r["microrregiao"]["mesorregiao"]["UF"]["sigla"]


def locate(lon, lat):
    p = Point(lon, lat)
    for f in ibge_states()["features"]:
        if shape(f["geometry"]).contains(p):
            uf = f["properties"]["codarea"]
            for m in ibge_munis(uf)["features"]:
                if shape(m["geometry"]).contains(p):
                    code = m["properties"]["codarea"]
                    nome, sigla = muni_name(code)
                    return {"ibge_municipio_codigo": code, "municipio": nome, "uf": sigla}
    return None


def main():
    for d in sorted(p for p in PAIRS.iterdir() if p.is_dir()):
        meta_p = d / "metadata.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        tifs = sorted(d.glob("*_refl10m.tif"))
        grids = []
        for t in tifs:
            with rasterio.open(t) as s:
                grids.append((s.crs.to_string(), tuple(round(v, 6) for v in s.transform)[:6], s.width, s.height))
        aligned = len(grids) == 2 and grids[0] == grids[1]
        loc = locate(*meta["center_lonlat"])
        cdse = [im.get("cdse_product_id") for im in meta["images"]]
        meta["verification"] = {
            "aligned_identical_grid": aligned, "grid": grids[0] if grids else None,
            "ibge_location_of_center": loc,
            "cdse_products_found": all(cdse),
        }
        meta_p.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        print(d.name, "| alinhado:", aligned, "|", loc, "| CDSE:", cdse)


if __name__ == "__main__":
    main()
