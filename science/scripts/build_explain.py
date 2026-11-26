"""Dados da tela ENTENDA O CASO, para cada caso publicado no jogo:

- composição do recorte no MapBiomas 10 m (Col. 4), nos dois anos, agrupada em classes legíveis;
- camadas de "onde é nativa" para o botão MAPA (1º ano: nativa; 2º ano: nativa + perdida + ganha),
  tiradas de data/pairs/<ID>/<ID>_labels10m.tif (mesma grade das imagens do jogo);
- etiquetas de "por que a imagem engana" (fogo, campo/rocha, plantio, estação, água), calculadas dos dados.

Saída: data/explain/<ID>.json e data/explain/<ID>_nat_a.png / _nat_b.png (export_game.py leva ao jogo).
Requer Google Earth Engine (GEE_PROJECT). Uso: python build_explain.py [IDs...]"""
import json
import sys
from pathlib import Path

import ee
import numpy as np
import rasterio
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import gee  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "explain"

# Grupos de exibição (legenda MapBiomas Col. 11 / Col. 4 10 m). "native" = entra na conta de vegetação nativa.
GROUPS = [
    ("forest", True, [3, 6, 49]),        # Formação Florestal, Floresta Alagável, Restinga Arbórea
    ("mangrove", True, [5]),
    ("savanna", True, [4, 7]),           # Formação Savânica, Savana Alagada
    ("grassland", True, [12, 77, 50, 84]),  # Campestre, Herbáceo-Arbustiva, Restinga Herbácea, Marisma
    ("wetland", True, [11]),             # Campo Alagado e Área Pantanosa
    ("rock", True, [29]),                # Afloramento Rochoso
    ("tidalflat", True, [32]),           # Apicum
    ("pasture", False, [15]),
    ("crop", False, [18, 19, 39, 20, 40, 62, 41, 36, 46, 47, 35, 48]),
    ("silviculture", False, [9]),
    ("mosaic", False, [21]),
    ("water", False, [26, 33, 31]),
    ("urban", False, [24]),
    ("mining", False, [30]),
    ("bare", False, [22, 23, 25, 75]),
]
assert sorted(c for _, n, cs in GROUPS if n for c in cs) == sorted(gee.NATIVE)


def classes_10m(m):
    l, b, r, t = m["aoi"]["bounds_utm"]; h, w = m["aoi"]["shape"]
    ya, yb = m["years"]
    l10 = ee.Image(gee.ASSETS["lulc10_c4"])
    img = ee.Image.cat([l10.select(f"classification_{ya}").rename("a"), l10.select(f"classification_{yb}").rename("b")]
                       ).unmask(0).toUint8()
    arr = ee.data.computePixels({"expression": img, "fileFormat": "NUMPY_NDARRAY",
        "grid": {"dimensions": {"width": w, "height": h},
                 "affineTransform": {"scaleX": 10, "shearX": 0, "translateX": l, "shearY": 0, "scaleY": -10, "translateY": t},
                 "crsCode": m["aoi"]["crs"]}})
    return np.asarray(arr["a"]), np.asarray(arr["b"])


def composition(cls):
    out = {}
    for key, _, codes in GROUPS:
        v = round(100 * float(np.isin(cls, codes).mean()), 1)
        if v > 0:
            out[key] = v
    other = round(100 - sum(out.values()), 1)
    if other >= 0.5:
        out["other"] = other
    return out


def overlay(n_a, n_b, which, size):
    """RGBA na grade do recorte, ampliada por vizinho mais próximo até o tamanho da imagem do jogo."""
    h, w = n_a.shape
    rgba = np.zeros((h, w, 4), np.uint8)
    if which == "a":
        rgba[n_a == 1] = (69, 224, 124, 70)          # nativa no 1º ano
    else:
        rgba[n_b == 1] = (69, 224, 124, 70)          # nativa no 2º ano
        rgba[(n_a == 1) & (n_b == 0)] = (255, 59, 59, 150)   # perdida
        rgba[(n_a == 0) & (n_b == 1)] = (255, 210, 63, 150)  # ganha
    return Image.fromarray(rgba, "RGBA").resize((size, size), Image.NEAREST)


def tags(comp_a, comp_b, fire, kind, season_hint, delta10):
    t = []
    if max(fire.values() or [0]) >= 20:
        t.append("fire")
    open_nat = sum(comp_a.get(k, 0) for k in ("grassland", "wetland", "rock", "savanna", "tidalflat"))
    if open_nat >= 40:
        t.append("open")
    if comp_a.get("silviculture", 0) + comp_b.get("silviculture", 0) >= 5 or kind == "trap":
        t.append("plantation")
    if comp_a.get("crop", 0) + comp_b.get("crop", 0) >= 10 and kind in ("trap", "gain", "stable_edge"):
        t.append("crop")
    if season_hint:
        t.append("season")
    if abs(comp_a.get("water", 0) + comp_a.get("wetland", 0) - comp_b.get("water", 0) - comp_b.get("wetland", 0)) >= 5:
        t.append("water")
    if kind == "loss" and delta10 <= -50:
        t.append("conversion")
    if kind == "gain":
        t.append("regrowth")
    return t


def main():
    gee.init()
    game = json.loads((ROOT / "game" / "public" / "data" / "challenges.json").read_text(encoding="utf-8"))
    ids = sys.argv[1:] or [c["id"] for c in game["challenges"]]
    by = {c["id"]: c for c in game["challenges"]}
    OUT.mkdir(parents=True, exist_ok=True)
    for cid in ids:
        d = ROOT / "data" / "pairs" / cid
        m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
        a, b = classes_10m(m)
        with rasterio.open(d / f"{cid}_labels10m.tif") as s:
            names = list(s.descriptions); L = s.read()
        n_a, n_b = L[names.index("n10_a")], L[names.index("n10_b")]
        # conferência: a composição do GEE e os rótulos salvos têm de dar a mesma % de nativa
        nat_gee = [100 * float(np.isin(x, gee.NATIVE).mean()) for x in (a, b)]
        nat_lbl = [100 * float(x.mean()) for x in (n_a, n_b)]
        assert all(abs(g - l) < 0.5 for g, l in zip(nat_gee, nat_lbl)), (cid, nat_gee, nat_lbl)
        size = m["display"]["game_image_px"]
        overlay(n_a, n_b, "a", size).save(OUT / f"{cid}_nat_a.png", optimize=True)
        overlay(n_a, n_b, "b", size).save(OUT / f"{cid}_nat_b.png", optimize=True)
        dz = json.loads((ROOT / "data" / "dossie" / f"{cid}.json").read_text(encoding="utf-8"))
        fire = {int(y): v for y, v in dz.get("fire_pct", {}).items()}
        pa = [p for p in dz.get("areas_protegidas", []) if p.get("frac", 0) >= 0.1]
        c = by.get(cid, {})
        comp_a, comp_b = composition(a), composition(b)
        rec = {
            "id": cid, "source": "MapBiomas Col. 4 (10 m), mesma grade do recorte; fogo: MapBiomas Fogo Col. 5.1; áreas protegidas: WDPA",
            "composition": {str(m["years"][0]): comp_a, str(m["years"][1]): comp_b},
            "fire_pct": fire,
            "protected": [{"name": p["nome"], "type": p["tipo"], "year": p["ano"], "pct": round(100 * p["frac"])} for p in pa],
            "tags": tags(comp_a, comp_b, fire, c.get("kind", m["mode"]), c.get("season_hint", False),
                         c.get("reference_pp", {}).get("mapbiomas_10m", 0)),
        }
        (OUT / f"{cid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        print(cid, rec["tags"], comp_a, flush=True)


if __name__ == "__main__":
    main()
