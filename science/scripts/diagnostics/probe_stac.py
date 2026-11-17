"""Testa os três endpoints STAC gratuitos de Sentinel-2 L2A (diagnóstico)."""
from pystac_client import Client

ENDPOINTS = [
    ("PlanetaryComputer", "https://planetarycomputer.microsoft.com/api/stac/v1", "sentinel-2-l2a"),
    ("EarthSearch-C1", "https://earth-search.aws.element84.com/v1", "sentinel-2-c1-l2a"),
    ("CDSE", "https://stac.dataspace.copernicus.eu/v1", "sentinel-2-l2a"),
]
BBOX = [-44.13, -20.13, -44.11, -20.11]  # Brumadinho/MG (teste)

for name, url, coll in ENDPOINTS:
    try:
        c = Client.open(url)
        items = list(c.search(collections=[coll], bbox=BBOX,
                              datetime="2020-07-01/2020-08-31", max_items=5).items())
        print(name, len(items), [(i.id, round(i.properties.get("eo:cloud_cover", -1), 1)) for i in items])
        if items:
            it = items[0]
            print("  assets:", sorted(it.assets.keys()))
            print("  props:", {k: v for k, v in it.properties.items()
                               if any(s in k.lower() for s in ("baseline", "processing", "offset", "mgrs", "orbit"))})
    except Exception as e:  # noqa: BLE001
        print(name, "ERR", repr(e)[:300])
