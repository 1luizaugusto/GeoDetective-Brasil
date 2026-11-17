"""Testa caminhos públicos (GCS) dos GeoTIFFs anuais de cobertura do MapBiomas Brasil
e, se existir, faz uma leitura por janela (COG) para confirmar acesso remoto."""
import os

import requests

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
BUCKET = "https://storage.googleapis.com/mapbiomas-public"
prefixes = ["initiatives/brasil/collection11/lulc/coverage", "initiatives/brasil/collection_11/lulc/coverage",
            "brasil/collection11/lulc/coverage", "initiatives/brasil/collection11/lclu/coverage"]
names = ["brazil_coverage-col11_{y}.tif", "brazil_coverage_{y}.tif", "brasil_coverage_{y}.tif"]
found = None
for p in prefixes:
    for n in names:
        u = f"{BUCKET}/{p}/{n.format(y=2024)}"
        r = requests.head(u, timeout=30)
        print(r.status_code, u)
        if r.status_code == 200 and not found:
            found = u
if found:
    import rasterio
    from rasterio.windows import from_bounds
    with rasterio.open("/vsicurl/" + found) as s:
        print(s.crs, s.res, s.shape, "overviews:", s.overviews(1), "tiled:", s.profile.get("tiled"))
        w = from_bounds(-59.94, -2.97, -59.90, -2.92, s.transform)
        a = s.read(1, window=w)
        import numpy as np
        print("Ducke 2024 classes:", dict(zip(*np.unique(a, return_counts=True))))
