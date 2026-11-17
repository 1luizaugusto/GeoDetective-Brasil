"""Verifica escala/offset radiométrico declarados nos itens Earth Search C1 (2020 vs 2024)."""
import json
from pystac_client import Client

c = Client.open("https://earth-search.aws.element84.com/v1")
for dt in ("2020-08-15/2020-08-31", "2024-08-15/2024-08-31"):
    it = next(c.search(collections=["sentinel-2-c1-l2a"], bbox=[-44.13, -20.13, -44.11, -20.11],
                       datetime=dt, max_items=1).items())
    a = it.assets["red"].to_dict()
    print(it.id, it.properties.get("s2:processing_baseline"))
    print("  red href:", a["href"])
    print("  raster:bands:", json.dumps(a.get("raster:bands")))
    print("  extra props:", {k: v for k, v in it.properties.items() if "offset" in k or "quantification" in k})
