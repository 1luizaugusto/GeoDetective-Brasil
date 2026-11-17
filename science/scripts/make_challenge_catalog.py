"""candidates_v0_verified.csv -> data/catalog/challenges_v1.json (entrada do build_from_catalog).

Regras (documentadas, sem resultado inventado):
 - modo do recorte vem da hipótese: "perda"→loss; "ganho (vegetação plantada)"→trap (Δ nativa≈0);
   "ganho"→gain; demais→stable_edge. A referência MapBiomas gravada no metadata é quem diz o Δ real.
 - janela sazonal da planilha; se a planilha alertou SEM_CENA_LIMPA, a janela é ampliada.
 - CER-01, CAP-AM e CAP-RO reutilizam as cenas já verificadas dos pilotos.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
PILOT_ITEMS = {
    "CER-01": ("S2B_T22KCC_20200530T134212_L2A", "S2B_T22KCC_20240529T134749_L2A"),
    "CAP-AM": ("S2B_T20MRB_20200721T141737_L2A", "S2B_T20MRB_20240720T141713_L2A"),
    "CAP-RO": ("S2B_T20LLQ_20200727T143729_L2A", "S2B_T20LLQ_20240726T144346_L2A"),
}
# Correções de coordenada (motivo registrado em notes)
COORD_FIX = {}


def mode_for(h: str) -> str:
    h = h.lower()
    if h.startswith("perda") or "perda de caatinga" in h:
        return "loss"
    if "plantada" in h:
        return "trap"
    if h.startswith("ganho"):
        return "gain"
    return "stable_edge"


out = []
for r in csv.DictReader(open(CAT / "candidates_v0_verified.csv", encoding="utf-8-sig")):
    s0, s1 = r["janela_sazonal"].split("/")
    notes = r["riscos"]
    if "SEM_CENA_LIMPA" in r["alertas"]:
        s0, s1 = "07-01", "12-31"
        notes += " | janela ampliada para 07-01/12-31 (sem cena limpa na janela original)"
    lon, lat = COORD_FIX.get(r["id"], (float(r["lon"]), float(r["lat"])))
    c = {"id": r["id"], "name": f"{r['localidade']}, {r['municipio_ibge'] or r['uf_esperada']}/{r['uf_ibge'] or r['uf_esperada']}",
         "group": r["grupo"], "biome": r["bioma_ibge"] or r["bioma_esperado"],
         "lon": lon, "lat": lat, "mode": mode_for(r["hipotese"]),
         "season": [s0, s1], "years": [2020, 2025],
         "hypothesis": r["hipotese"], "notes": notes}
    if r["id"] in PILOT_ITEMS:
        c["item_a"], c["item_b"] = PILOT_ITEMS[r["id"]]
        c["search"] = 6000
    out.append(c)

(CAT / "challenges_v1.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
from collections import Counter  # noqa: E402
print(len(out), Counter(c["mode"] for c in out))
