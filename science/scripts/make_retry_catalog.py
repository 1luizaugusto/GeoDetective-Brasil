"""Gera data/catalog/challenges_retry.json com os desafios cujo ÚLTIMO registro no build_log falhou,
relaxando os critérios de busca de cena (documentado no metadata.notes):
  - janela sazonal = ano inteiro (o par ainda é escolhido pela menor diferença de dia do ano)
  - min_valid 0,5 na área de busca (o recorte final continua exigindo >= 99% de pixels válidos)
  - avalia até 30 cenas por ano (em vez de 10)
Também aplica correções de coordenada (COORD_FIX) — sempre conferidas na API de malhas do IBGE.
Uso: python make_retry_catalog.py <catalogo.json> [<catalogo2.json> ...]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
COORD_FIX = {  # id: (lon, lat, motivo)
    "CAP-GO": (-49.37, -16.69, "coordenada original caía em Aparecida de Goiânia; nova conferida no IBGE (5208707 Goiânia)"),
}

last = {}
for line in (CAT / "build_log.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line); last[r["id"]] = r
entries = [c for p in sys.argv[1:] for c in json.loads(Path(p).read_text(encoding="utf-8"))]
out = []
for c in entries:
    failed = c["id"] in last and not last[c["id"]]["ok"]
    if not failed and c["id"] not in COORD_FIX:
        continue
    c = dict(c)
    if c["id"] in COORD_FIX:
        lon, lat, why = COORD_FIX[c["id"]]
        c["lon"], c["lat"] = lon, lat
        c["notes"] = f"{c.get('notes', '')} | {why}".strip(" |")
    if failed:
        c.update(season=["01-01", "12-31"], min_valid=0.5, max_eval=30)
        c["notes"] = f"{c.get('notes', '')} | busca relaxada (ano inteiro, min_valid 0,5, 30 cenas) por excesso de nuvem".strip(" |")
    out.append(c)
(CAT / "challenges_retry.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(len(out), [c["id"] for c in out])
