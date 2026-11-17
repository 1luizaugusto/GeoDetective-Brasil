"""Refaz os casos pendentes com triagem CDSE e preferência pelo ano mais recente (2025) → challenges_fix5.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
base = {}
for p in ("challenges_v1.json", "challenges_retry.json", "challenges_fix.json", "challenges_fix3.json", "challenges_fix4.json"):
    for c in json.loads((CAT / p).read_text(encoding="utf-8")):
        base[c["id"]] = c  # o último catálogo vence (exclusões acumuladas)

out = []
for cid in ("CAP-PB", "CAP-RR", "CER-03", "CAP-BA", "CAP-RN"):
    c = dict(base[cid])
    c["years"] = [2020, 2025]  # build_pair cai para 2024/2021 se não houver par
    c.pop("item_a", None); c.pop("item_b", None)
    c["notes"] = f"{c.get('notes', '')} | rodada 5: triagem CDSE, preferência 2025".strip(" |")
    out.append(c)
(CAT / "challenges_fix5.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print([(c["id"], c.get("exclude"), c.get("search"), c.get("min_valid")) for c in out])
