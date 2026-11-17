"""Bioma de um ponto pelo limite oficial do IBGE (Biomas 1:250.000, 2019).
Fonte: https://geoftp.ibge.gov.br/informacoes_ambientais/estudos_ambientais/biomas/vetores/Biomas_250mil.zip
(descompactado em data/external/ibge_biomas/, fora do git)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

SHP = Path(__file__).resolve().parents[2] / "data" / "external" / "ibge_biomas" / "lm_bioma_250.shp"


@lru_cache(maxsize=1)
def _load():
    from pyogrio.raw import read
    from shapely import from_wkb
    from shapely.strtree import STRtree
    meta, _, geom, fields = read(SHP)
    names = meta["fields"].tolist()
    col = next(i for i, n in enumerate(names) if n.lower().startswith("bioma"))
    geoms = [from_wkb(g) for g in geom]
    labels = [str(v) for v in fields[col]]
    return STRtree(geoms), geoms, labels, meta.get("crs")


def biome_of(lon: float, lat: float) -> str | None:
    """Nome do bioma IBGE (ex.: 'Cerrado', 'Mata Atlântica') ou None fora do Brasil.
    O shapefile está em SIRGAS 2000 geográfico, compatível com WGS84 na escala do jogo."""
    from shapely.geometry import Point
    tree, geoms, labels, _ = _load()
    p = Point(lon, lat)
    for i in tree.query(p):
        if geoms[i].contains(p):
            return labels[i]
    return None
