"""Acesso aos produtos MapBiomas no Google Earth Engine (GEE).

IDs dos assets copiados da página oficial em 2026-11-12:
https://brasil.mapbiomas.org/downloads/assets-no-google-earth-engine/
Códigos de legenda: "Códigos de Legenda — MapBiomas Brasil Coleção 11" (PDF oficial, ago/2026),
cópia em data/external/mapbiomas/legenda_col11.txt.

Requer: conta GEE (uso não comercial) + projeto Google Cloud registrado.
Autenticação (uma vez):  earthengine authenticate
Projeto: variável de ambiente GEE_PROJECT ou argumento --project.
"""
from __future__ import annotations

import os

import ee

ASSETS = {
    "lulc30_c11": "projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_coverage_v3",
    "lulc10_c4": "projects/mapbiomas-public/assets/brazil/lulc_10m/collection4/mapbiomas_10m_collection4_coverage_v1",
    "defor_secveg_c11": "projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_deforestation_secondary_vegetation_v5",
    "fire_annual_c51": "projects/mapbiomas-public/assets/brazil/fire/collection5_1/mapbiomas_fire_collection51_annual_burned_v1",
    "fire_year_last_c51": "projects/mapbiomas-public/assets/brazil/fire/collection5_1/mapbiomas_fire_collection51_year_last_fire_v1",
}

# Coleção 11 — vegetação NATIVA (decisão do projeto, 2026-11-12):
#   1. Floresta: 3 Formação Florestal, 6 Floresta Alagável, 4 Formação Savânica,
#                7 Savana Alagada (beta), 5 Mangue, 49 Restinga Arbórea
#   2. Vegetação Herbácea e Arbustiva: 12 Formação Campestre, 77 Formação Herbáceo Arbustiva,
#                11 Campo Alagado e Área Pantanosa, 84 Marisma (beta), 50 Restinga Herbácea/Arbustiva,
#                32 Apicum, 29 Afloramento Rochoso
NATIVE_FOREST = [3, 6, 4, 7, 5, 49]
NATIVE_NONFOREST = [12, 77, 11, 84, 50, 32, 29]
NATIVE = NATIVE_FOREST + NATIVE_NONFOREST
SILVICULTURE = [9]  # 3.3 Silvicultura — não-alvo (explicitamente)
WATER = [33, 31]    # 5.1 Rio, Lago e Oceano; 5.2 Aquicultura (legenda Col. 11)


def init(project: str | None = None):
    project = project or os.environ.get("GEE_PROJECT")
    if not project:
        raise SystemExit("Defina o projeto GEE: --project <id> ou variável GEE_PROJECT")
    ee.Initialize(project=project)


def band_for_year(img: ee.Image, year: int) -> ee.Image:
    """Assets anuais do MapBiomas são imagens multibanda 'classification_<ano>'."""
    return img.select(f"classification_{year}")


def native_mask(year: int, asset: str = "lulc30_c11") -> ee.Image:
    cls = band_for_year(ee.Image(ASSETS[asset]), year)
    return cls.remap(NATIVE, [1] * len(NATIVE), 0).rename("native")


def is_in(cls: ee.Image, codes) -> ee.Image:
    return cls.remap(list(codes), [1] * len(codes), 0)


def masks_on_grid(grid, year_a: int, year_b: int):
    """Máscaras MapBiomas EXATAMENTE na grade UTM 10 m do par (computePixels, nearest).
    Retorna dict de arrays uint8: n10_a/n10_b (nativa, 10 m Col.4), n30_a/n30_b (nativa, 30 m Col.11),
    s30_a/s30_b (silvicultura, 30 m Col.11)."""
    import numpy as np
    l30 = ee.Image(ASSETS["lulc30_c11"]); l10 = ee.Image(ASSETS["lulc10_c4"])
    img = ee.Image.cat([
        is_in(l10.select(f"classification_{year_a}"), NATIVE).rename("n10_a"),
        is_in(l10.select(f"classification_{year_b}"), NATIVE).rename("n10_b"),
        is_in(l30.select(f"classification_{year_a}"), NATIVE).rename("n30_a"),
        is_in(l30.select(f"classification_{year_b}"), NATIVE).rename("n30_b"),
        is_in(l30.select(f"classification_{year_a}"), SILVICULTURE).rename("s30_a"),
        is_in(l30.select(f"classification_{year_b}"), SILVICULTURE).rename("s30_b"),
        is_in(l30.select(f"classification_{year_a}"), WATER).rename("w30_a"),
    ]).unmask(0).toUint8()
    req = {"expression": img, "fileFormat": "NUMPY_NDARRAY",
           "grid": {"dimensions": {"width": grid.width, "height": grid.height},
                    "affineTransform": {"scaleX": grid.res, "shearX": 0, "translateX": grid.left,
                                        "shearY": 0, "scaleY": -grid.res, "translateY": grid.top},
                    "crsCode": f"EPSG:{grid.epsg}"}}
    arr = ee.data.computePixels(req)
    return {n: np.asarray(arr[n]) for n in arr.dtype.names}


def pair_years(meta: dict) -> list[int]:
    """Anos das duas imagens do par (a partir das datas de aquisição)."""
    return [int(im["datetime_utc"][:4]) for im in meta["images"]]


def aoi_from_metadata(meta: dict) -> ee.Geometry:
    """Retângulo EXATO do recorte do jogo, na projeção UTM do par."""
    l, b, r, t = meta["aoi"]["bounds_utm"]
    return ee.Geometry.Rectangle([l, b, r, t], proj=meta["aoi"]["crs"], geodesic=False)
