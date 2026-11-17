"""QA visual, rodada 2 (folhas data/qa/qa_fix_*.png) → data/catalog/challenges_fix3.json.
Exclusões são CUMULATIVAS: cenas já rejeitadas antes continuam fora."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
base = {c["id"]: c for p in ("challenges_v1.json", "challenges_gain_v1.json", "challenges_fix.json", "challenges_fix2.json")
        for c in json.loads((CAT / p).read_text(encoding="utf-8"))}


def cur_ids(cid):
    m = json.loads((ROOT / "data" / "pairs" / cid / "metadata.json").read_text(encoding="utf-8"))
    return [im["earth_search_id"] for im in m["images"]]


# id: (motivo, quais imagens atuais excluir [0,1], ajustes)
FIX = {
    "CAP-AM": ("busca de 6 km toda em floresta; usa o centro do PILOTO-03 (borda da reserva)", [],
               {"lon": -59.965, "lat": -2.955, "search": 6000}),
    "CER-03": ("busca de 8 km toda em campo nativo; busca ampliada para 16 km para alcançar a borda do parque", [],
               {"search": 16000}),
    "CAP-MA": ("nuvem pequena na data 'depois'", [1], {}),
    "CAP-PB": ("nuvens pequenas nas duas datas", [0, 1], {"season": ["07-01", "12-31"], "max_eval": 30, "min_valid": 0.5}),
    "CAP-RR": ("nuvem e fumaça na data 'antes'", [0], {}),
    "CAP-SE": ("nuvem pequena na data 'depois'", [1], {}),
}
out = []
for cid, (why, bad, upd) in FIX.items():
    c = dict(base[cid]); c.update(upd)
    ids = cur_ids(cid)
    c["exclude"] = sorted(set(c.get("exclude", [])) | {ids[i] for i in bad})
    if bad:
        c.pop("item_a", None); c.pop("item_b", None)
    c["notes"] = f"{c.get('notes', '')} | QA visual 2: {why}".strip(" |")
    out.append(c)
(CAT / "challenges_fix3.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print([(c["id"], c.get("exclude")) for c in out])
