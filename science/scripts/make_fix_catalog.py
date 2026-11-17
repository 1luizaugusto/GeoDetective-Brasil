"""Reconstruções decididas no QA visual (lote 1) → data/catalog/challenges_fix.json.
Cada entrada guarda o motivo em notes. Cenas rejeitadas vão em `exclude` (lidas do metadata atual)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
base = {c["id"]: c for p in ("challenges_v1.json", "challenges_gain_v1.json")
        for c in json.loads((CAT / p).read_text(encoding="utf-8"))}

# id: (motivo, índice da imagem a excluir: 0=antes, 1=depois, None=nenhuma)
FIX = {
    "CAP-MA": ("imagem preta (bug de nodata no tom, corrigido)", None),
    "CAP-SE": ("imagem preta (bug de nodata no tom, corrigido)", None),
    "CMP-01": ("imagem preta (bug de nodata no tom, corrigido)", None),
    "GAN-01": ("imagem preta (bug de nodata no tom, corrigido)", None),
    "GAN-03": ("imagem preta (bug de nodata no tom, corrigido)", None),
    "CAP-AM": ("recorte sem borda (floresta contínua): exige borda visível", None),
    "CER-03": ("recorte sem borda (100% nativo): exige borda visível", None),
    "CMP-02": ("floresta uniforme super-contrastada: faixa mínima de contraste", None),
    "CAP-PB": ("nuvens pequenas e sombras não marcadas pelo SCL na data 'depois'", 1),
    "CAP-RR": ("pluma de fumaça/nuvem na data 'antes'", 0),
    "CAP-RS": ("nuvens pequenas na data 'depois'", 1),
}
FIX2 = {  # lote 2 do QA visual
    "PAM-03": ("nuvem na data 'depois'", 1),
    "PAN-03": ("recorte ~75% rio: penalidade de água no posicionamento", None),
}
import sys  # noqa: E402
if "--batch2" in sys.argv:
    FIX = FIX2
out = []
for cid, (why, bad) in FIX.items():
    c = dict(base[cid])
    m = json.loads((ROOT / "data" / "pairs" / cid / "metadata.json").read_text(encoding="utf-8"))
    c["notes"] = f"{c.get('notes', '')} | QA visual: {why}".strip(" |")
    if bad is not None:
        c["exclude"] = [m["images"][bad]["earth_search_id"]]
        c.pop("item_a", None); c.pop("item_b", None)
    if cid in ("CAP-PB",):
        c.update(season=["07-01", "12-31"], max_eval=30, min_valid=0.5)
    out.append(c)
(CAT / ("challenges_fix2.json" if "--batch2" in sys.argv else "challenges_fix.json")).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print([(c["id"], c.get("exclude")) for c in out])
