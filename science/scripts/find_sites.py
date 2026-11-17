"""Acervo extra: acha locais candidatos DIRETO nas máscaras MapBiomas Col. 11 (30 m), sem coordenadas escritas à mão.

Fase 1 (scan): o Brasil é dividido em blocos de 4°×4°. Cada bloco vira uma grade de células de ~2,4 km com a FRAÇÃO de
nativa, silvicultura, formação aberta e água em ano A e ano B (média dos pixels de 30 m, via GEE computePixels).
Resultado em cache: data/external/mb_cells/<ya>_<yb>/tile_<lon>_<lat>.npz (fora do git; ~2 min por bloco no GEE).

Fase 2 (seleção), focada nas fraquezas do modelo (docs/03 §4):
  trap        silvicultura cresce ≥ 25 pp e nativa fica estável (|Δ| ≤ 3 pp)        → modo trap
  open_edge   formação nativa aberta (campo/savana) ≥ 30%, nativa 30–70%, Δ ≈ 0      → modo stable_edge
  open_loss   perda de formação aberta ≥ 15 pp e de nativa ≥ 15 pp                   → modo loss
Locais a ≥ 40 km uns dos outros e dos desafios existentes; município (IBGE, malhas) e bioma (IBGE 1:250 mil).
Saída: data/catalog/challenges_extra_v1.json (group "extra").
Uso: python find_sites.py [--scan-only] [--per-kind 12] [--workers 6] [--out NOME]"""
import argparse
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import ee
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from geodet import gee  # noqa: E402
from geodet.biomes import _load as _biomes, biome_of  # noqa: E402
from verify_pairs import locate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
OPEN = [4, 12, 77, 50]  # Formação Savânica, Campestre, Herbáceo-Arbustiva, Restinga Herbácea (legenda Col. 11)
D = 0.0216               # ~2,4 km no equador
N = 186                  # células por lado de um bloco de 4°
BANDS = ["nat_a", "nat_b", "silv_a", "silv_b", "open_a", "open_b", "water"]

ap = argparse.ArgumentParser()
ap.add_argument("--per-kind", type=int, default=12); ap.add_argument("--workers", type=int, default=6)
ap.add_argument("--ya", type=int, default=2020); ap.add_argument("--yb", type=int, default=2025)
ap.add_argument("--scan-only", action="store_true"); ap.add_argument("--no-scan", action="store_true", help="só seleção, com o cache atual"); ap.add_argument("--out", default="challenges_extra_v1.json")
ap.add_argument("--project", default="geodetective-brasil")
ap.add_argument("--kinds", nargs="+", default=["trap", "open_edge", "open_loss"])
ap.add_argument("--id-start", type=int, default=1, help="numeração inicial dos IDs (evita colidir com acervos anteriores)")
ap.add_argument("--per-kind-map", nargs="*", default=[], help="KIND=N para sobrepor --per-kind")
a = ap.parse_args()
CACHE = ROOT / "data" / "external" / "mb_cells" / f"{a.ya}_{a.yb}"
CACHE.mkdir(parents=True, exist_ok=True)


def cell_image():
    l30 = ee.Image(gee.ASSETS["lulc30_c11"])
    ca, cb = l30.select(f"classification_{a.ya}"), l30.select(f"classification_{a.yb}")
    frac = ee.Image.cat([
        gee.is_in(ca, gee.NATIVE).rename("nat_a"), gee.is_in(cb, gee.NATIVE).rename("nat_b"),
        gee.is_in(ca, gee.SILVICULTURE).rename("silv_a"), gee.is_in(cb, gee.SILVICULTURE).rename("silv_b"),
        gee.is_in(ca, OPEN).rename("open_a"), gee.is_in(cb, OPEN).rename("open_b"),
        gee.is_in(ca, gee.WATER).rename("water"),
    ]).toFloat()
    # duas etapas (30 m → 300 m → célula): uma etapa só estoura o tempo do GEE
    mid = frac.reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(crs="EPSG:4326", scale=300)
    return mid.reduceResolution(ee.Reducer.mean(), maxPixels=1024)


def tiles_over_brazil():
    from shapely.geometry import box
    _, geoms, _, _ = _biomes()
    out = []
    for L in range(-74, -34, 4):
        for T in range(6, -34, -4):
            b = box(L, T - 4, L + 4, T)
            if any(g.intersects(b) for g in geoms):
                out.append((L, T))
    return out


def scan_tile(img, L, T):
    f = CACHE / f"tile_{L}_{T}.npz"
    if f.exists():
        return f, "cache"
    def px(l, t, n):
        arr = ee.data.computePixels({"expression": img, "fileFormat": "NUMPY_NDARRAY",
            "grid": {"dimensions": {"width": n, "height": n},
                     "affineTransform": {"scaleX": D, "shearX": 0, "translateX": l, "shearY": 0, "scaleY": -D, "translateY": t},
                     "crsCode": "EPSG:4326"}})
        return {b: np.asarray(arr[b], dtype=np.float32) for b in BANDS}
    try:
        out, how = px(L, T, N), "novo"
    except ee.EEException as e:
        if "timed out" not in str(e):
            raise
        # bloco denso (ex.: Amazônia): 4 sub-blocos de N/2 células na MESMA grade
        h = N // 2
        out = {b: np.full((N, N), np.nan, np.float32) for b in BANDS}
        for oy in (0, h):
            for ox in (0, h):
                sub = px(L + ox * D, T - oy * D, h)
                for b in BANDS:
                    out[b][oy:oy + h, ox:ox + h] = sub[b]
        how = "novo (4 sub-blocos)"
    np.savez_compressed(f, **out, L=L, T=T)
    return f, how


gee.init(a.project)
tiles = tiles_over_brazil()
img = cell_image()
todo = [] if a.no_scan else [t for t in tiles if not (CACHE / f"tile_{t[0]}_{t[1]}.npz").exists()]
print(f"{len(tiles)} blocos sobre o Brasil; {len(todo)} a varrer")
with ThreadPoolExecutor(a.workers) as ex:
    futs = {ex.submit(scan_tile, img, L, T): (L, T) for L, T in todo}
    for i, fu in enumerate(as_completed(futs), 1):
        try:
            print(f"  [{i}/{len(todo)}] bloco {futs[fu]}: {fu.result()[1]}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] bloco {futs[fu]}: FALHOU {repr(e)[:120]}", flush=True)
if a.scan_only:
    sys.exit(0)

# ---- fase 2: seleção --------------------------------------------------------------------------
rows = []
for f in sorted(CACHE.glob("tile_*.npz")):
    z = np.load(f); L, T = float(z["L"]), float(z["T"])
    v = {b: z[b] for b in BANDS}
    dn, ds, do = v["nat_b"] - v["nat_a"], v["silv_b"] - v["silv_a"], v["open_b"] - v["open_a"]
    ok = np.isfinite(dn) & (v["water"] < 0.15)
    kinds = {
        "trap": (ok & (ds >= 0.25) & (np.abs(dn) <= 0.03), ds),
        "open_edge": (ok & (v["open_a"] >= 0.3) & (v["nat_a"] >= 0.3) & (v["nat_a"] <= 0.7) & (np.abs(dn) <= 0.02), v["open_a"]),
        "open_loss": (ok & (do <= -0.15) & (dn <= -0.15), -dn),
        # floresta (pouca formação aberta): onde o modelo acerta melhor
        "forest_loss": (ok & (v["open_a"] < 0.1) & (dn <= -0.15) & (np.abs(ds) < 0.02), -dn),
        # perda PARCIAL de floresta (25–70 pp): sobra borda dos dois lados; o modelo erra perdas totais (lição XTR-F01/F03/F05)
        "forest_partial": (ok & (v["open_a"] < 0.1) & (v["nat_a"] >= 0.8) & (dn <= -0.25) & (dn >= -0.7) & (np.abs(ds) < 0.02), -np.abs(dn + 0.45)),
        # mata que VOLTOU (intervalo longo, ex. 2017→2025): ganho de nativa fora de formação aberta
        # (evita "pasto reclassificado como campo nativo", lição GAN-04), sem plantio e com pouca água (lição GAN-01..03)
        "regrowth": (ok & (v["water"] < 0.05) & (v["nat_a"] <= 0.6) & (dn >= 0.20) & (np.abs(do) <= 0.05) & (np.abs(ds) < 0.02), dn),
        "forest_edge": (ok & (v["open_a"] < 0.1) & (v["nat_a"] >= 0.35) & (v["nat_a"] <= 0.65) & (np.abs(dn) <= 0.01)
                        & (np.abs(ds) < 0.02), -np.abs(v["nat_a"] - 0.5)),
    }
    for kind, (m, s) in kinds.items():
        for y, x in zip(*np.nonzero(m)):
            rows.append({"kind": kind, "s": float(s[y, x]), "lon": L + (x + 0.5) * D, "lat": T - (y + 0.5) * D,
                         **{b: float(v[b][y, x]) for b in BANDS}})


def km(p, q):
    return 111.2 * math.hypot((p[0] - q[0]) * math.cos(math.radians((p[1] + q[1]) / 2)), p[1] - q[1])


taken = []
for p in CAT.glob("challenges_*.json"):
    if p.name == a.out:
        continue
    taken += [(c["lon"], c["lat"]) for c in json.loads(p.read_text(encoding="utf-8"))]

MODE = {"regrowth": "gain", "forest_partial": "loss", "trap": "trap", "open_edge": "stable_edge", "open_loss": "loss", "forest_loss": "loss", "forest_edge": "stable_edge"}
# nomes neutros: o nome não pode entregar a resposta do desafio
LABEL = {"regrowth": "Floresta e áreas abertas", "forest_partial": "Floresta e áreas abertas", "trap": "Chapadões rurais", "open_edge": "Vegetação e roças", "open_loss": "Vegetação e roças",
         "forest_loss": "Floresta e áreas abertas", "forest_edge": "Floresta e áreas abertas"}
CODE = {"regrowth": "R", "forest_partial": "D", "trap": "T", "open_edge": "E", "open_loss": "L", "forest_loss": "F", "forest_edge": "B"}
out = []
for kind in a.kinds:
    cands = sorted((r for r in rows if r["kind"] == kind), key=lambda r: -r["s"])
    limit = dict(kv.split("=") for kv in a.per_kind_map).get(kind); limit = int(limit) if limit else a.per_kind
    print(kind, len(cands), "células candidatas")
    per_biome, n = {}, 0
    for r in cands:
        if n >= limit:
            break
        pt = (r["lon"], r["lat"])
        if any(km(pt, q) < 40 for q in taken):
            continue
        bio = biome_of(*pt)
        if not bio or per_biome.get(bio, 0) >= max(2, math.ceil(a.per_kind / 3)):  # espalha entre biomas
            continue
        if kind in ("open_loss", "regrowth") and bio == "Pantanal":  # "perda" de campo no Pantanal = cheia/seca (lição GAN-01..03)
            continue
        loc = locate(*pt)
        if not loc:
            continue
        n += 1; per_biome[bio] = per_biome.get(bio, 0) + 1; taken.append(pt)
        cid = f"XTR-{CODE[kind]}{n + a.id_start - 1:02d}"
        out.append({
            "id": cid, "name": f"{LABEL[kind]}, {loc['municipio']}/{loc['uf']}",
            "group": "extra", "biome": bio, "lon": round(pt[0], 5), "lat": round(pt[1], 5),
            "mode": MODE[kind], "years": [a.ya, a.yb], "season": ["01-01", "12-31"], "min_valid": 0.7, "max_eval": 30,
            "hypothesis": {"regrowth": "ganho", "forest_partial": "perda", "trap": "armadilha", "open_edge": "estável", "open_loss": "perda", "forest_loss": "perda", "forest_edge": "estável"}[kind],
            "notes": (f"find_sites.py ({kind}): célula ~2,4 km MapBiomas 30 m — nativa {r['nat_a']:.2f}→{r['nat_b']:.2f}, "
                      f"silvicultura {r['silv_a']:.2f}→{r['silv_b']:.2f}, aberta {r['open_a']:.2f}→{r['open_b']:.2f}"),
        })
        print(" ", cid, bio, loc["municipio"], loc["uf"], round(r["s"], 2), flush=True)
(CAT / a.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(len(out), "locais →", CAT / a.out)
