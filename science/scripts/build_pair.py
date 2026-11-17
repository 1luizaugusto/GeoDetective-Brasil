"""Gera um DESAFIO (par Sentinel-2 L2A C1 + referência MapBiomas), otimizado para visão humana.

Fluxo:
 1. Escolhe o par de cenas (ou usa IDs fixos): mesma estação, SCL válido, sem fumaça.
 2. Baixa via Earth Engine as máscaras MapBiomas (nativa 10 m Col.4 / 30 m Col.11,
    silvicultura) na MESMA grade UTM 10 m da área de busca.
 3. Posiciona o recorte do jogo (padrão 2,4 km) conforme `mode`:
      loss  → maior perda nativa      gain → maior ganho nativo
      stable_edge → Δ≈0 com borda visível   trap → maior expansão de silvicultura (Δ nativa≈0)
 4. Lê as 10 bandas só no recorte; grava GeoTIFF 10 m, imagem do jogo (×3, tom do par),
    contexto (área de busca a 20 m) e metadata.json com a referência MapBiomas do recorte.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw
from pyproj import Transformer
from pystac_client import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import gee, pairing, render, s2  # noqa: E402
from geodet.s2 import Grid  # noqa: E402

BAND_ORDER = ["blue", "green", "red", "rededge1", "rededge2", "rededge3", "nir", "nir08", "swir16", "swir22"]


def get_item(item_id):
    return Client.open(s2.EARTH_SEARCH).get_collection(s2.COLLECTION).get_item(item_id)


def save_tif(path, arrs, grid, dtype, nodata, descriptions, tags):
    prof = dict(driver="GTiff", width=grid.width, height=grid.height, count=len(arrs), dtype=dtype,
                crs=f"EPSG:{grid.epsg}", transform=grid.transform, nodata=nodata,
                compress="deflate", predictor=2, tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(path, "w", **prof) as dst:
        for i, (a, d) in enumerate(zip(arrs, descriptions), 1):
            dst.write(a.astype(dtype), i)
            dst.set_band_description(i, d)
        dst.update_tags(**tags)


def box_sums(a, n):
    """Somas de todas as janelas n×n via imagem integral."""
    c = np.pad(a.astype("float64"), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    return c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]


def choose_crop(m, valid, n, mode, step=6, vis_change=None):
    N = float(n * n)
    V = box_sums(valid, n) / N
    A = box_sums(m["n10_a"], n) / N; B = box_sums(m["n10_b"], n) / N
    A30 = box_sums(m["n30_a"], n) / N; B30 = box_sums(m["n30_b"], n) / N
    d10, d30 = B - A, B30 - A30
    mix = np.minimum(A, 1 - A)
    if mode == "loss":
        score = -(d10 + d30) / 2 + 0.05 * mix
    elif mode == "gain":
        score = (d10 + d30) / 2 + 0.05 * mix
    elif mode == "trap":
        S = (box_sums(m["s30_b"], n) - box_sums(m["s30_a"], n)) / N
        score = S - 2 * np.abs(d30) - 2 * np.abs(d10)
    else:  # stable_edge: Δ≈0 nos dois mapas, com contraste (borda) visível
        score = mix - 4 * np.maximum(np.abs(d10), np.abs(d30)) - 3 * np.maximum(0, 0.15 - mix)  # exige borda visível
        if vis_change is not None:  # evita "estável" no mapa mas com mudança visível (rebrota, obra)
            score = score - 3 * box_sums(vis_change, n) / N
    score = score - 2 * np.abs(d10 - d30)  # mapas 10 m e 30 m discordantes = referência duvidosa (ex.: CAP-MA)
    if "w30_a" in m:  # recorte dominado por rio/lago não é desafio de vegetação
        score = score - 3 * np.maximum(0, box_sums(m["w30_a"], n) / N - 0.2)
    score = np.where(V >= 0.99, score, -np.inf)
    sub = np.full(score.shape, -np.inf); sub[::step, ::step] = score[::step, ::step]  # mantém grade de 60 m
    y, x = np.unravel_index(np.argmax(sub), sub.shape)
    if not np.isfinite(sub[y, x]):
        return None
    return int(x), int(y), {"native10_a": float(A[y, x]), "native10_b": float(B[y, x]),
                            "native30_a": float(A30[y, x]), "native30_b": float(B30[y, x])}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--lon", type=float, required=True); ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--mode", choices=["loss", "gain", "stable_edge", "trap"], default="stable_edge")
    ap.add_argument("--season", nargs=2, default=["06-01", "09-30"])
    ap.add_argument("--years", nargs=2, type=int, default=[2020, 2025])  # 2025 = último ano com MapBiomas (referência e rótulos)
    ap.add_argument("--item-a"); ap.add_argument("--item-b")
    ap.add_argument("--search", type=float, default=8000)
    ap.add_argument("--min-valid", type=float, default=0.9)
    ap.add_argument("--max-eval", type=int, default=10)
    ap.add_argument("--haze-max", type=float, help="limiar de névoa só p/ áreas de areia/dunas (falso positivo); fumaça fica com o QA visual")
    ap.add_argument("--exclude", nargs="*", default=[], help="IDs de cenas rejeitadas no QA visual (ex.: nuvem pequena que o SCL não marcou)")
    ap.add_argument("--crop", type=int, default=240); ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--hypothesis", default=""); ap.add_argument("--notes", default="")
    ap.add_argument("--group", default=""); ap.add_argument("--biome", default="")
    ap.add_argument("--project", default="geodetective-brasil")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "data" / "pairs"))
    a = ap.parse_args(argv)
    gee.init(a.project)
    pairing.HAZE_MAX = a.haze_max if a.haze_max is not None else pairing.HAZE_DEFAULT  # não vaza entre itens do lote

    # 1) par de cenas (fallbacks de área e de ano)
    pair = None
    # mais recente primeiro; 2026+ não tem referência MapBiomas ainda
    year_opts = list(dict.fromkeys([tuple(a.years), (a.years[0], 2025), (a.years[0], 2024), (2021, 2025), (2021, 2024)]))
    for size in (a.search, 6000, 4000):
        G = s2.make_grid(a.lon, a.lat, size, 10.0)
        if a.item_a and a.item_b:
            ia, ib = get_item(a.item_a), get_item(a.item_b)
            pair = ((s2.scl_valid_fraction(ia, G)[0], ia, pairing.haze_fraction(ia, G)),
                    (s2.scl_valid_fraction(ib, G)[0], ib, pairing.haze_fraction(ib, G)))
            break
        for ya, yb in year_opts:
            pair, _, _ = pairing.choose_pair(G, ya, yb, tuple(a.season), min_valid=a.min_valid, max_eval=a.max_eval,
                                             exclude=a.exclude)
            if pair:
                break
        if pair:
            break
    if not pair:
        raise SystemExit(f"{a.id}: nenhum par válido (nuvem/fumaça/cobertura) nas janelas testadas")
    (fa, ia, ha), (fb, ib, hb) = pair
    ya, yb = ia.datetime.year, ib.datetime.year
    print(a.id, ia.id, ib.id, f"busca={G.width*10/1000:g} km")

    # 2) máscaras MapBiomas na grade de busca + validade S2 (SCL 20 m → 10 m)
    m = gee.masks_on_grid(G, ya, yb)
    G20 = G.at(20.0)
    valid = np.ones((G.height, G.width), bool)
    for it in (ia, ib):
        scl = s2._read(it.assets["scl"].href, G20, dtype="uint8")
        valid &= np.isin(scl, s2.SCL_VALID).repeat(2, 0).repeat(2, 1)[:G.height, :G.width]
    vis = None
    if a.mode == "stable_edge":
        nd = []
        for it in (ia, ib):
            r = s2.read_reflectance(it, G, ("red", "nir"))
            nd.append((r["nir"] - r["red"]) / (r["nir"] + r["red"] + 1e-6))
        vis = np.nan_to_num(np.abs(nd[1] - nd[0]) > 0.2).astype("float32")
    sel = choose_crop(m, valid, a.crop, a.mode, vis_change=vis)
    if sel is None:
        raise SystemExit(f"{a.id}: nenhum recorte com >=99% de pixels válidos")
    x0, y0, fr = sel
    C = Grid(G.epsg, G.left + x0 * 10, G.top - y0 * 10, a.crop, a.crop, 10.0)
    sl = (slice(y0, y0 + a.crop), slice(x0, x0 + a.crop))
    cx, cy = C.left + a.crop * 5, C.top - a.crop * 5
    clon, clat = Transformer.from_crs(C.epsg, 4326, always_xy=True).transform(cx, cy)

    out = Path(a.out) / a.id; out.mkdir(parents=True, exist_ok=True)
    # reconstrução: apaga saídas da versão anterior (datas antigas confundiam QA e treino)
    for pat in ("game_*.png", "context_*.png", "pair_*.png", "*_refl10m.tif", "*_scl10m.tif", "*_labels10m.tif"):
        for f in out.glob(pat):
            f.unlink()
    # 3) recorte 10 bandas + contexto RGB 20 m
    crops, ctx = [], []
    for it in (ia, ib):
        r = s2.read_reflectance(it, C, BAND_ORDER)
        scl = s2.read_scl(it, C)
        crops.append((r, scl, np.isin(scl, s2.SCL_VALID)))
        ctx.append(s2.read_reflectance(it, G20, ("red", "green", "blue")))
    vb = crops[0][2] & crops[1][2]
    tone = render.pair_tone(crops[0][0], crops[1][0], valid=vb)
    ctx_tone = render.pair_tone(ctx[0], ctx[1])

    dates, metas, games, ctxs = [], [], [], []
    for (rc, sclc, vc), rctx, it, frac, hz in zip(crops, ctx, (ia, ib), (fa, fb), (ha, hb)):
        d = it.datetime.date().isoformat()
        stack = [np.where(np.isfinite(rc[b]), np.round(rc[b] * 10000), -32768) for b in BAND_ORDER]
        tags = dict(source_item=it.id, source=s2.EARTH_SEARCH, collection=s2.COLLECTION,
                    scale="0.0001", units="surface reflectance", created=datetime.now(timezone.utc).isoformat())
        save_tif(out / f"{a.id}_{d}_refl10m.tif", stack, C, "int16", -32768,
                 [f"{b}({s2.BANDS[b][0]})" for b in BAND_ORDER], tags)
        save_tif(out / f"{a.id}_{d}_scl10m.tif", [sclc], C, "uint8", 0, ["SCL"], tags)
        g = render.upscale(render.apply_tone(rc, tone), a.zoom); g.save(out / f"game_{d}.png", optimize=True)
        cimg = Image.fromarray(render.apply_tone(rctx, ctx_tone))
        ImageDraw.Draw(cimg).rectangle([x0 // 2, y0 // 2, (x0 + a.crop) // 2 - 1, (y0 + a.crop) // 2 - 1],
                                       outline=(255, 214, 0), width=2)
        cimg.save(out / f"context_{d}.png", optimize=True)
        games.append(g); ctxs.append(cimg)
        b_, r_ = rc["blue"], rc["red"]; ok = np.isfinite(b_)
        meta = s2.item_summary(it)
        meta["search_valid_fraction_scl"] = round(frac, 4)
        meta["search_haze_fraction"] = round(hz, 4)
        meta["crop_valid_fraction_scl"] = round(float(vc.mean()), 4)
        meta["crop_haze_fraction"] = round(float(((b_ > 0.06) & (b_ >= 0.95 * r_))[ok].mean()), 4)
        meta["cdse_product_id"] = s2.find_cdse_id(it)
        if meta["cdse_product_id"]:
            meta["cdse_stac_item_url"] = f"{s2.CDSE_STAC}/collections/sentinel-2-l2a/items/{meta['cdse_product_id']}"
            mo = re.search(r"_R(\d{3})_", meta["cdse_product_id"])
            meta["relative_orbit"] = int(mo.group(1)) if mo else None
        meta["copernicus_browser_url"] = s2.cdse_browser_url(clon, clat, it.datetime.date(), zoom=14)
        dates.append(d); metas.append(meta)

    km = a.crop * 10 / 1000
    render.side_by_side(games[0], games[1], f"{dates[0]}  ({ia.id})", f"{dates[1]}  ({ib.id})",
                        f"{a.id} — {a.name}  [{km:g} km, 10 m nativo ×{a.zoom}]",
                        out / "pair_game.png", scale_px=50 * a.zoom, scale_m=500)
    render.side_by_side(ctxs[0], ctxs[1], dates[0], dates[1],
                        f"{a.id} — busca {G.width*10/1000:g} km (recorte em amarelo)",
                        out / "pair_context.png", scale_px=50, scale_m=1000)

    ref = {k: round(100 * float(v[sl].mean()), 2) for k, v in m.items()}
    reference = {
        "source": "MapBiomas Brasil — Col. 4 (10 m, Sentinel-2) e Col. 11 (30 m, Landsat), via Google Earth Engine",
        "assets": {"10m": gee.ASSETS["lulc10_c4"], "30m": gee.ASSETS["lulc30_c11"]},
        "native_classes_col11": gee.NATIVE,
        f"native_pct_10m_{ya}": ref["n10_a"], f"native_pct_10m_{yb}": ref["n10_b"],
        "delta_pp_10m": round(ref["n10_b"] - ref["n10_a"], 2),
        f"native_pct_30m_{ya}": ref["n30_a"], f"native_pct_30m_{yb}": ref["n30_b"],
        "delta_pp_30m": round(ref["n30_b"] - ref["n30_a"], 2),
        f"silviculture_pct_30m_{ya}": ref["s30_a"], f"silviculture_pct_30m_{yb}": ref["s30_b"],
        "note": "Referência independente para validar o modelo; não é verdade absoluta (MapBiomas também tem erros).",
    }
    flags = []
    if min(metas[0]["crop_valid_fraction_scl"], metas[1]["crop_valid_fraction_scl"]) < 0.99:
        flags.append("VALIDO<99%")
    if max(metas[0]["crop_haze_fraction"], metas[1]["crop_haze_fraction"]) > pairing.HAZE_MAX:
        flags.append("NEVOA/FUMACA?")
    if abs(reference["delta_pp_10m"] - reference["delta_pp_30m"]) > 10:
        flags.append("MAPAS_DIVERGEM>10pp")
    l, b, rr, t = C.bounds
    meta_all = {
        "challenge_id": a.id, "name": a.name, "group": a.group, "biome": a.biome, "mode": a.mode,
        "selection_hypothesis": a.hypothesis, "notes": a.notes, "years": [ya, yb],
        "target_definition": "vegetação nativa (MapBiomas: Floresta + Vegetação Herbácea e Arbustiva); silvicultura, agricultura e pastagem = não-alvo",
        "search_center_lonlat": [a.lon, a.lat], "center_lonlat": [round(clon, 6), round(clat, 6)],
        "aoi": {"crs": f"EPSG:{C.epsg}", "bounds_utm": [l, b, rr, t], "size_m": a.crop * 10,
                "bbox_lonlat": [round(v, 6) for v in C.bbox_lonlat()], "pixel_size_m": 10.0, "shape": [a.crop, a.crop]},
        "crop_selection": {"mode": a.mode, "search_size_m": G.width * 10, "offset_px": [x0, y0],
                           "based_on": "máscaras MapBiomas (nativa 10 m + 30 m; silvicultura 30 m)"},
        "display": {"zoom_factor": a.zoom, "resampling": "Lanczos (sem super-resolução)",
                    "game_image_px": a.crop * a.zoom, "tone": tone},
        "images": metas,
        "doy_difference_days": min(abs(s2.doy(ia) - s2.doy(ib)), 365 - abs(s2.doy(ia) - s2.doy(ib))),
        "same_mgrs_tile": metas[0]["mgrs_tile"] == metas[1]["mgrs_tile"],
        "same_relative_orbit": (metas[0].get("relative_orbit") is not None
                                and metas[0].get("relative_orbit") == metas[1].get("relative_orbit")),
        "bands_10m_stack": [f"{b_}({s2.BANDS[b_][0]})" for b_ in BAND_ORDER],
        "reference_mapbiomas": reference,
        "model_estimate": None,
        "qa": {"auto_flags": flags, "visual": "pendente"},
        "license": "Copernicus Sentinel Data Legal Notice; MapBiomas CC-BY 4.0",
        "attribution": f"Contains modified Copernicus Sentinel data {ya}, {yb}; MapBiomas Brasil Col. 4 e 11",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out / "metadata.json").write_text(json.dumps(meta_all, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ok Δ10m={reference['delta_pp_10m']:+.1f} Δ30m={reference['delta_pp_30m']:+.1f} pp  flags={flags}")
    return meta_all


if __name__ == "__main__":
    main()
