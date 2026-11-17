"""Acesso a Sentinel-2 L2A (Collection 1) via STAC público, sem autenticação.

Fonte primária: Earth Search (Element 84) — coleção `sentinel-2-c1-l2a`, COGs no
AWS Open Data (bucket público). Escolhida porque o arquivo 2020 está reprocessado
pela ESA no baseline 05.00 (Collection 1), radiometricamente consistente com 2024
(baseline 05.1x). Proveniência oficial é registrada também no catálogo STAC do
Copernicus Data Space Ecosystem (CDSE), que contém o mesmo produto ESA.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import date

import numpy as np
import rasterio
from pyproj import Transformer
from pystac_client import Client
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from shapely.geometry import box, shape
from shapely.ops import transform as shp_transform

EARTH_SEARCH = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-c1-l2a"
CDSE_STAC = "https://stac.dataspace.copernicus.eu/v1"

# Bandas usadas: nome Earth Search -> banda ESA, resolução nativa (m)
BANDS = {
    "blue": ("B02", 10), "green": ("B03", 10), "red": ("B04", 10), "nir": ("B08", 10),
    "rededge1": ("B05", 20), "rededge2": ("B06", 20), "rededge3": ("B07", 20),
    "nir08": ("B8A", 20), "swir16": ("B11", 20), "swir22": ("B12", 20),
    "coastal": ("B01", 60),
}
# Scene Classification (SCL): classes consideradas válidas para análise
#  4 vegetação, 5 solo exposto, 6 água, 7 não classificado (11 neve: irrelevante no BR)
# inválidas: 0 sem dado, 1 saturado/defeituoso, 2 área escura/topográfica,
#  3 sombra de nuvem, 8/9 nuvem média/alta prob., 10 cirrus
SCL_VALID = (4, 5, 6, 7)

os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")


def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32700 if lat < 0 else 32600) + zone


@dataclass
class Grid:
    """Grade-alvo fixa (UTM) — garante que as duas datas tenham pixels idênticos."""
    epsg: int
    left: float
    top: float
    width: int
    height: int
    res: float

    @property
    def transform(self):
        return from_origin(self.left, self.top, self.res, self.res)

    @property
    def bounds(self):
        return (self.left, self.top - self.height * self.res,
                self.left + self.width * self.res, self.top)

    def at(self, res: float) -> "Grid":
        f = res / self.res
        return Grid(self.epsg, self.left, self.top, int(round(self.width / f)),
                    int(round(self.height / f)), res)

    def bbox_lonlat(self):
        t = Transformer.from_crs(self.epsg, 4326, always_xy=True)
        l, b, r, tp = self.bounds
        xs, ys = t.transform([l, r, l, r], [b, b, tp, tp])
        return (min(xs), min(ys), max(xs), max(ys))


def make_grid(lon: float, lat: float, size_m: float, res: float = 10.0) -> Grid:
    """Quadrado de `size_m` centrado em (lon, lat), encaixado na grade de 60 m do S2."""
    epsg = utm_epsg(lon, lat)
    x, y = Transformer.from_crs(4326, epsg, always_xy=True).transform(lon, lat)
    half = size_m / 2
    snap = 60.0
    left = math.floor((x - half) / snap) * snap
    top = math.ceil((y + half) / snap) * snap
    n = int(round(size_m / res))
    return Grid(epsg, left, top, n, n, res)


def search(grid: Grid, start: str, end: str, max_tile_cloud: float = 60.0):
    """Itens que cobrem TOTALMENTE a área (footprint de dados contém o AOI)."""
    bbox = grid.bbox_lonlat()
    aoi = box(*bbox)
    c = Client.open(EARTH_SEARCH)
    items = c.search(collections=[COLLECTION], bbox=list(bbox), datetime=f"{start}/{end}",
                     query={"eo:cloud_cover": {"lt": max_tile_cloud}}).item_collection()
    out = [it for it in items if shape(it.geometry).buffer(-1e-4).contains(aoi)]
    out.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))
    return out


def _read(href: str, grid: Grid, resampling=Resampling.nearest, dtype="uint16"):
    with rasterio.open(href) as src:
        with WarpedVRT(src, crs=f"EPSG:{grid.epsg}", transform=grid.transform,
                       width=grid.width, height=grid.height, resampling=resampling,
                       src_nodata=0, nodata=0) as vrt:
            return vrt.read(1).astype(dtype)


def scl_valid_fraction(item, grid: Grid) -> tuple[float, np.ndarray]:
    scl = _read(item.assets["scl"].href, grid.at(20.0))
    valid = np.isin(scl, SCL_VALID)
    return float(valid.mean()), scl


def read_reflectance(item, grid: Grid, names=("blue", "green", "red", "nir")) -> dict[str, np.ndarray]:
    """Reflectância de superfície (float32) = DN*scale + offset, conforme raster:bands do item.
    Bandas de 20 m são reamostradas bilinearmente para a grade de 10 m."""
    out = {}
    for n in names:
        a = item.assets[n]
        rb = (a.extra_fields.get("raster:bands") or [{}])[0]
        scale, offset = rb.get("scale", 1e-4), rb.get("offset", 0.0)
        native = BANDS[n][1]
        rs = Resampling.nearest if native <= grid.res else Resampling.bilinear
        dn = _read(a.href, grid, rs, "float32")
        refl = dn * scale + offset
        refl[dn == 0] = np.nan
        out[n] = refl.astype("float32")
    return out


def read_scl(item, grid: Grid) -> np.ndarray:
    return _read(item.assets["scl"].href, grid, Resampling.nearest, "uint8")


def doy(item) -> int:
    return item.datetime.timetuple().tm_yday


def item_summary(item) -> dict:
    p = item.properties
    return {
        "earth_search_id": item.id,
        "datetime_utc": item.datetime.isoformat(),
        "platform": p.get("platform"),
        "mgrs_tile": f"{p.get('mgrs:utm_zone')}{p.get('mgrs:latitude_band')}{p.get('mgrs:grid_square')}",
        "relative_orbit": p.get("sat:relative_orbit"),
        "processing_baseline": p.get("s2:processing_baseline"),
        "esa_product_uri": p.get("s2:product_uri"),
        "tile_cloud_cover_pct": p.get("eo:cloud_cover"),
        "sun_elevation_deg": p.get("view:sun_elevation"),
        "stac_item_url": f"{EARTH_SEARCH}/collections/{COLLECTION}/items/{item.id}",
    }


def find_cdse_id(item) -> str | None:
    """Localiza o mesmo produto ESA no STAC do Copernicus Data Space (proveniência oficial)."""
    p = item.properties
    tile = f"T{p.get('mgrs:utm_zone')}{p.get('mgrs:latitude_band')}{p.get('mgrs:grid_square')}"
    d = item.datetime.date().isoformat()
    try:
        c = Client.open(CDSE_STAC)
        g = item.geometry
        cands = c.search(collections=["sentinel-2-l2a"], intersects=g,
                         datetime=f"{d}T00:00:00Z/{d}T23:59:59Z", max_items=20).items()
        ids = [x.id for x in cands if tile in x.id]
        # prefere baseline >= 05 (Collection 1)
        ids.sort(key=lambda s: ("_N05" not in s, s))
        return ids[0] if ids else None
    except Exception:  # noqa: BLE001
        return None


def cdse_browser_url(lon: float, lat: float, day: date, zoom: int = 13) -> str:
    d = day.isoformat()
    return ("https://browser.dataspace.copernicus.eu/?zoom={z}&lat={lat:.5f}&lng={lon:.5f}"
            "&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&layerId=1_TRUE_COLOR"
            "&fromTime={d}T00%3A00%3A00.000Z&toTime={d}T23%3A59%3A59.999Z").format(
                z=zoom, lat=lat, lon=lon, d=d)
