"""Confere se os links de proveniência gravados em data/pairs/*/metadata.json respondem (HTTP 200)."""
import json
from pathlib import Path

import requests

PAIRS = Path(__file__).resolve().parents[2] / "data" / "pairs"
for m in sorted(PAIRS.glob("*/metadata.json")):
    meta = json.loads(m.read_text(encoding="utf-8"))
    for im in meta["images"]:
        for k in ("stac_item_url", "cdse_stac_item_url"):
            u = im.get(k)
            if not u:
                print(meta["challenge_id"], k, "AUSENTE"); continue
            r = requests.get(u, timeout=60)
            ok = r.status_code == 200 and r.json().get("id") in u
            im[f"{k}_http_ok"] = ok
            print(meta["challenge_id"], k, r.status_code, "OK" if ok else "FALHA")
    m.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
