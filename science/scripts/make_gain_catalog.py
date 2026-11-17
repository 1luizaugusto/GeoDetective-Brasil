"""native_gain_candidates.csv (busca MapBiomas Col.11 via GEE) -> data/catalog/challenges_gain_v1.json.
Pega as melhores células por região, afastadas >= 10 km entre si. Coordenadas = centro da célula de 2,4 km
encontrada pelo GEE (não inventadas). O Δ real é medido de novo pelo build_pair na grade do par."""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
PER_REGION = 3
SEASON = {"pantanal_mt": ["06-01", "09-30"], "cerrado_go_df": ["05-01", "08-31"],
          "amazonia_nordeste_para": ["07-01", "11-30"], "mata_atlantica_vale_paraiba": ["05-01", "09-30"]}
BIOME = {"pantanal_mt": "Pantanal", "cerrado_go_df": "Cerrado",
         "amazonia_nordeste_para": "Amazônia", "mata_atlantica_vale_paraiba": "Mata Atlântica"}
NAME = {"pantanal_mt": "Pantanal (MT)", "cerrado_go_df": "Cerrado (GO/DF)",
        "amazonia_nordeste_para": "Nordeste do Pará", "mata_atlantica_vale_paraiba": "Vale do Paraíba (SP/RJ)"}

rows = list(csv.DictReader(open(CAT / "native_gain_candidates.csv", encoding="utf-8-sig")))
rows.sort(key=lambda r: -float(r["ganho_nativo_pct_celula"]))
picked = {}
for r in rows:
    reg = r["regiao"]; lon, lat = float(r["lon"]), float(r["lat"])
    if float(r["ganho_nativo_pct_celula"]) < 5:
        continue
    lst = picked.setdefault(reg, [])
    if len(lst) >= PER_REGION:
        continue
    if all(math.hypot((lon - x) * 111 * math.cos(math.radians(lat)), (lat - y) * 111) >= 10 for x, y, _ in lst):
        lst.append((lon, lat, r))

out, n = [], 0
for reg, lst in picked.items():
    for lon, lat, r in lst:
        n += 1
        note = f"célula GEE: ganho {r['ganho_nativo_pct_celula']}%, perda {r['perda_nativa_pct_celula']}%, nativa 2020 {r['nativa_2020_pct']}%"
        if reg == "pantanal_mt":
            note += " | CAUTELA: no Pantanal o 'ganho' pode ser dinâmica de cheia/fogo, não regeneração"
        out.append({"id": f"GAN-{n:02d}", "name": f"Ganho nativo — {NAME[reg]}", "group": "complementar_ganho",
                    "biome": BIOME[reg], "lon": lon, "lat": lat, "mode": "gain", "season": SEASON[reg],
                    "years": [2020, 2025], "hypothesis": "ganho de vegetação nativa (regeneração) segundo MapBiomas",
                    "notes": note})
(CAT / "challenges_gain_v1.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
for c in out:
    print(c["id"], c["biome"], c["lon"], c["lat"], c["notes"][:60])
