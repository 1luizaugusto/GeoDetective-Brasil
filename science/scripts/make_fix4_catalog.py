"""QA visual, rodada 3 (após correção do bug de arquivos antigos na folha) → challenges_fix4.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
base = {}
for p in ("challenges_v1.json", "challenges_retry.json", "challenges_fix.json", "challenges_fix3.json"):
    for c in json.loads((CAT / p).read_text(encoding="utf-8")):
        base[c["id"]] = c  # o último catálogo vence (exclusões acumuladas)


def cur(cid):
    m = json.loads((ROOT / "data" / "pairs" / cid / "metadata.json").read_text(encoding="utf-8"))
    return [im["earth_search_id"] for im in m["images"]]


FIX = {
    "CAP-PB": ("nuvens na data 'antes' (2020-10-04)", [0], {}),
    "CAP-RR": ("fumaça/nuvem pequena na data 'antes' (2021-01-20)", [0], {}),
    "CER-03": ("busca de 16 km não coube num único tile; tenta 12 km", [], {"search": 12000}),
    "CAP-BA": ("sem par válido nas tentativas anteriores; critérios mais frouxos", [],
               {"season": ["01-01", "12-31"], "min_valid": 0.3, "max_eval": 40}),
}
out = []
for cid, (why, bad, upd) in FIX.items():
    c = dict(base[cid]); c.update(upd)
    if bad:
        ids = cur(cid)
        c["exclude"] = sorted(set(c.get("exclude", [])) | {ids[i] for i in bad})
        c.pop("item_a", None); c.pop("item_b", None)
    c["notes"] = f"{c.get('notes', '')} | QA visual 3: {why}".strip(" |")
    out.append(c)
(CAT / "challenges_fix4.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print([(c["id"], c.get("exclude"), c.get("search")) for c in out])
