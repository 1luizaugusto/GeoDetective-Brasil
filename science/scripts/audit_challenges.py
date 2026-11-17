"""Auditoria dos desafios do jogo: o que mudou de fato em cada recorte, com evidências INDEPENDENTES.

Para cada desafio de game/public/data/challenges.json:
  1. Transições de classe no MapBiomas 30 m (Col. 11, Landsat) e no 10 m (Col. 4, Sentinel-2), na grade exata do recorte:
     nativa → não-nativa (desmatamento: para onde foi), não-nativa → nativa (regeneração: de onde veio),
     ganho de silvicultura (plantio comercial — NÃO é nativa).
  2. NDVI das próprias imagens do jogo: mediana geral e ΔNDVI nos pixels que perderam / ganharam nativa.
  3. Veredito: o tipo de mudança comprovado (desmatamento / regeneração / armadilha de plantio / estável)
     precisa bater com o modo do desafio E aparecer nos dois mapas; senão o caso é sinalizado.
Saída: data/qa/auditoria_desafios.csv e data/qa/auditoria_desafios.md
Uso: python audit_challenges.py [--ids ID ...] [--all-pairs]"""
import argparse
import csv
import json
import sys
from pathlib import Path

import ee
import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import gee  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NAMES = {  # legenda oficial Col. 11 (data/external/mapbiomas/legenda_col11.txt)
    3: "Formação Florestal", 4: "Formação Savânica", 5: "Mangue", 6: "Floresta Alagável", 7: "Savana Alagada",
    49: "Restinga Arbórea", 11: "Campo Alagado", 12: "Formação Campestre", 77: "Herbáceo-Arbustiva",
    84: "Marisma", 50: "Restinga Herbácea", 32: "Apicum", 29: "Afloramento Rochoso",
    15: "Pastagem", 18: "Agricultura", 19: "Lavoura Temporária", 39: "Soja", 20: "Cana", 40: "Arroz",
    62: "Algodão", 41: "Outras Lav. Temporárias", 36: "Lavoura Perene", 46: "Café", 47: "Citrus", 35: "Dendê",
    48: "Outras Lav. Perenes", 9: "Silvicultura", 21: "Mosaico de Usos", 22: "Área não Vegetada",
    23: "Praia/Duna", 24: "Área Urbanizada", 30: "Mineração", 75: "Usina Fotovoltaica", 25: "Outras não Vegetadas",
    26: "Corpo d'Água", 33: "Rio/Lago/Oceano", 31: "Aquicultura", 0: "sem dado",
}
NAT = set(gee.NATIVE)
EXPECT = {"loss": "desmatamento", "gain": "regeneração", "trap": "armadilha de plantio", "stable_edge": "estável"}


def classes_on_grid(m):
    l, b, r, t = m["aoi"]["bounds_utm"]; h, w = m["aoi"]["shape"]
    ya, yb = m["years"]
    l30 = ee.Image(gee.ASSETS["lulc30_c11"]); l10 = ee.Image(gee.ASSETS["lulc10_c4"])
    img = ee.Image.cat([l30.select(f"classification_{ya}").rename("c30a"), l30.select(f"classification_{yb}").rename("c30b"),
                        l10.select(f"classification_{ya}").rename("c10a"), l10.select(f"classification_{yb}").rename("c10b")]
                       ).unmask(0).toUint8()
    arr = ee.data.computePixels({"expression": img, "fileFormat": "NUMPY_NDARRAY",
        "grid": {"dimensions": {"width": w, "height": h},
                 "affineTransform": {"scaleX": 10, "shearX": 0, "translateX": l, "shearY": 0, "scaleY": -10, "translateY": t},
                 "crsCode": m["aoi"]["crs"]}})
    return {k: np.asarray(arr[k]) for k in ("c30a", "c30b", "c10a", "c10b")}


def ndvi(path):
    with rasterio.open(path) as s:
        names = list(s.descriptions); A = s.read().astype("float32")
    nir = A[names.index("nir(B08)")]; red = A[names.index("red(B04)")]
    with np.errstate(invalid="ignore", divide="ignore"):
        return (nir - red) / (nir + red)


def top(cls, mask, k=3):
    if not mask.any():
        return ""
    u, c = np.unique(cls[mask], return_counts=True)
    o = np.argsort(-c)[:k]
    return "; ".join(f"{NAMES.get(int(u[i]), u[i])} {100 * c[i] / mask.sum():.0f}%" for i in o)


def analyse(cid):
    d = ROOT / "data" / "pairs" / cid
    m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    C = classes_on_grid(m)
    out = {"id": cid, "mode": m["mode"], "biome": m.get("biome", ""), "years": f"{m['years'][0]}-{m['years'][1]}"}
    for res in ("30", "10"):
        a, b = C[f"c{res}a"], C[f"c{res}b"]
        na, nb = np.isin(a, list(NAT)), np.isin(b, list(NAT))
        lost, gained = na & ~nb, ~na & nb
        out[f"perda_{res}m_pp"] = round(100 * lost.mean(), 1)
        out[f"ganho_{res}m_pp"] = round(100 * gained.mean(), 1)
        out[f"silv_{res}m"] = f"{100 * (a == 9).mean():.0f}→{100 * (b == 9).mean():.0f}%"
        out[f"silv_ganho_{res}m_pp"] = round(100 * ((b == 9).mean() - (a == 9).mean()), 1)
        out[f"perda_virou_{res}m"] = top(b, lost)
        out[f"ganho_veio_de_{res}m"] = top(a, gained)
        out[f"classes_a_{res}m"] = top(a, np.ones_like(a, bool), 4)
        out[f"classes_b_{res}m"] = top(b, np.ones_like(b, bool), 4)
        C[f"lost{res}"], C[f"gain{res}"] = lost, gained
    refl = sorted(d.glob(f"{cid}_*_refl10m.tif"))
    va, vb = ndvi(refl[0]), ndvi(refl[1])
    out["ndvi_mediana"] = f"{np.nanmedian(va):.2f}→{np.nanmedian(vb):.2f}"
    both_lost = C["lost10"] & C["lost30"]; both_gain = C["gain10"] & C["gain30"]
    dv = vb - va
    out["dNDVI_perda"] = round(float(np.nanmedian(dv[both_lost])), 2) if both_lost.sum() > 50 else ""
    out["dNDVI_ganho"] = round(float(np.nanmedian(dv[both_gain])), 2) if both_gain.sum() > 50 else ""
    silv_new = (C["c10b"] == 9) & (C["c30b"] == 9) & (C["c10a"] != 9) & (C["c30a"] != 9)
    out["dNDVI_plantio"] = round(float(np.nanmedian(dv[silv_new])), 2) if silv_new.sum() > 50 else ""

    # veredito: o que os DOIS mapas sustentam
    net10 = out["ganho_10m_pp"] - out["perda_10m_pp"]; net30 = out["ganho_30m_pp"] - out["perda_30m_pp"]
    sg = min(out["silv_ganho_10m_pp"], out["silv_ganho_30m_pp"])
    if sg >= 20 and abs(net10) <= 5 and abs(net30) <= 5:
        story = "armadilha de plantio"
    elif net10 <= -3 and net30 <= -3:
        story = "desmatamento"
    elif net10 >= 3 and net30 >= 3:
        story = "regeneração"
    elif abs(net10) < 3 and abs(net30) < 3:
        story = "estável"
    else:
        story = "MAPAS DISCORDAM"
    out["comprovado"] = story
    flags = []
    exp = EXPECT[m["mode"]]
    if story != exp and not (exp == "desmatamento" and story == "estável" and min(out["perda_10m_pp"], out["perda_30m_pp"]) >= 1):
        flags.append(f"modo={exp} mas evidência={story}")
    if story == "desmatamento" and out["dNDVI_perda"] != "" and out["dNDVI_perda"] > -0.05:
        flags.append(f"NDVI não caiu onde os mapas dizem perda ({out['dNDVI_perda']})")
    if story == "regeneração" and out["dNDVI_ganho"] != "" and out["dNDVI_ganho"] < 0.05:
        flags.append(f"NDVI não subiu onde os mapas dizem ganho ({out['dNDVI_ganho']})")
    if story == "armadilha de plantio" and out["dNDVI_plantio"] != "" and out["dNDVI_plantio"] < 0.1:
        flags.append(f"plantio sem aumento de NDVI ({out['dNDVI_plantio']})")
    if story == "regeneração" and "Silvicultura" in out["ganho_veio_de_10m"]:
        flags.append("ganho vindo de silvicultura (corte de plantio?)")
    out["alertas"] = " | ".join(flags)
    out["veredito"] = "OK" if not flags else "REVISAR"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*"); ap.add_argument("--project", default="geodetective-brasil")
    a = ap.parse_args()
    gee.init(a.project)
    ids = a.ids or [c["id"] for c in json.loads((ROOT / "game" / "public" / "data" / "challenges.json")
                                               .read_text(encoding="utf-8"))["challenges"]]
    rows = []
    for cid in ids:
        try:
            r = analyse(cid)
        except Exception as e:  # noqa: BLE001
            r = {"id": cid, "veredito": "ERRO", "alertas": repr(e)[:200]}
        rows.append(r)
        print(f"{cid:8s} {r.get('mode',''):11s} {r.get('comprovado',''):22s} {r['veredito']:7s} {r.get('alertas','')}", flush=True)
    out = ROOT / "data" / "qa"; out.mkdir(parents=True, exist_ok=True)
    prev = out / "auditoria_desafios.csv"
    if a.ids and prev.exists():  # auditoria parcial: mescla com a anterior por ID (não apaga os outros casos)
        new = {r["id"] for r in rows}
        rows = [r for r in csv.DictReader(prev.open(encoding="utf-8")) if r["id"] not in new] + rows
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(out / "auditoria_desafios.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    lines = ["# Auditoria dos desafios\n", f"{sum(r['veredito'] == 'OK' for r in rows)}/{len(rows)} OK\n",
             "| ID | modo | comprovado | perda 10/30 m | ganho 10/30 m | perda virou (10 m) | NDVI | ΔNDVI perda | alertas |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r.get('mode','')} | {r.get('comprovado','')} | {r.get('perda_10m_pp','')}/{r.get('perda_30m_pp','')} | "
                     f"{r.get('ganho_10m_pp','')}/{r.get('ganho_30m_pp','')} | {r.get('perda_virou_10m','')} | {r.get('ndvi_mediana','')} | "
                     f"{r.get('dNDVI_perda','')} | {r.get('alertas','')} |")
    (out / "auditoria_desafios.md").write_text("\n".join(lines), encoding="utf-8")
    print(out / "auditoria_desafios.md")


if __name__ == "__main__":
    main()
