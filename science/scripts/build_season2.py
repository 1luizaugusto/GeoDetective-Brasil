"""Segundo par de cenas: o PICO VERDE de cada ano (estação chuvosa), no MESMO recorte 10 m.

Por quê: com uma foto só por ano, mata caducifólia na seca (Caatinga, Cerrado) parece pasto — o modelo
erra e o jogador não tem como saber. O MapBiomas usa o ano inteiro. Com seca + chuva em cada ano, modelo e
jogador veem a mesma informação: a mata cinza na seca fica verde na chuva; o pasto seco não fica igual.

Regra (a mesma nos dois anos, para a comparação continuar justa):
  - candidatas: todas as datas do MESMO ano civil (o rótulo MapBiomas é anual) com cobertura 100%,
    SCL válido >= 99% NO RECORTE e sem névoa (triagem CDSE, 20 m), a >= 45 dias da data principal;
  - escolhida: a de maior NDVI médio no recorte = o momento mais verde daquele ano.
  A chuva não cai no mesmo dia todo ano; casar pelo estado da vegetação (pico verde) é mais justo do que
  casar pelo calendário. A diferença de dia do ano entre os dois anos fica registrada.
Saída: data/pairs/<ID>/season2/ (GeoTIFF 10 bandas, SCL, imagem do jogo, contexto) + metadata["season2"].
Uso: python build_season2.py [--only ID ...] [--force]"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pair import BAND_ORDER, save_tif  # noqa: E402
from geodet import cdse, pairing, render, s2  # noqa: E402
from geodet.s2 import Grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MIN_GAP_DAYS = 45
MAX_DOY_DIFF = 30
HAZE_STRICT = 0.006  # calibração (diagnostics/calib_haze.py): cenas limpas <= 0,006; nuvenzinha que o SCL não marca passa de 0,03


# datas reprovadas no QA visual (nuvem pequena que SCL e s2cloudless não marcaram): {ID: [datas]}
QA_EXCLUDE_FILE = ROOT / "data" / "catalog" / "season2_exclude.json"


def greenest(grid, d0: date, exclude=()):
    """Datas limpas do ano de d0, da mais verde para a menos verde."""
    st = cdse.screen_dates(grid, f"{d0.year}-01-01", f"{d0.year}-12-31", max_cc=100, res=20.0)
    # limites RELATIVOS ao local: certos recortes têm artefato permanente (solo claro conta como "névoa",
    # pixel sempre inválido no SCL). A data tem de ser tão limpa quanto os dias mais limpos DAQUELE recorte.
    full = [r for r in st if r["coverage"] >= 0.999 and r["valid"] >= 0.99]
    if not full:
        return [], {r["date"]: r.get("ndvi") for r in st}
    vmax = max(r["valid"] for r in full)
    hbase = float(np.percentile([r["haze"] for r in full], 20))
    vmin, hmax = max(0.99, vmax - 0.002), max(HAZE_STRICT, hbase + HAZE_STRICT)
    ok = {r["date"]: r for r in full if r["valid"] >= vmin and r["haze"] <= hmax
          and r["date"] not in exclude and (r.get("clm") is not None and r["clm"] <= 0.002)
          and r.get("ndvi") is not None and abs((date.fromisoformat(r["date"]) - d0).days) >= MIN_GAP_DAYS}
    return sorted(((r["ndvi"], d) for d, r in ok.items()), key=lambda t: -t[0]), {r["date"]: r.get("ndvi") for r in st}


def doy(ds):
    return date.fromisoformat(ds).timetuple().tm_yday


def item_on(grid, ds):
    """Item Earth Search da data (busca só aquele dia: rápido)."""
    its = s2.search(grid, ds, ds, max_tile_cloud=100)
    return its[0] if its else None


def tile(it):
    p = it.properties
    return (p.get("mgrs:utm_zone"), p.get("mgrs:latitude_band"), p.get("mgrs:grid_square"))


def build(d: Path, force=False):
    mp = d / "metadata.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    cid = m["challenge_id"]
    if m.get("season2") and not force:
        return "já tem"
    l, b, r, t = m["aoi"]["bounds_utm"]; h, w = m["aoi"]["shape"]
    C = Grid(int(m["aoi"]["crs"].split(":")[1]), l, t, w, h, 10.0)
    d0 = [date.fromisoformat(im["datetime_utc"][:10]) for im in m["images"]]
    excl = json.loads(QA_EXCLUDE_FILE.read_text(encoding="utf-8")).get(cid, []) if QA_EXCLUDE_FILE.exists() else []
    A, nda = greenest(C, d0[0], excl); B, ndb = greenest(C, d0[1], excl)
    if not A or not B:
        m["season2"] = {"status": "sem_cena", "detail": f"A={len(A)} B={len(B)} cenas limpas no ano"}
        mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        return m["season2"]["detail"]
    # par mais verde que os DOIS anos têm na MESMA época: maximiza o verde do ano mais fraco
    pairs = []
    for gva, da in A:
        for gvb, db in B:
            dd = abs(doy(da) - doy(db)); dd = min(dd, 365 - dd)
            if dd <= MAX_DOY_DIFF:
                pairs.append((min(gva, gvb) - 0.002 * dd, gva, da, gvb, db, dd))
    pairs.sort(key=lambda t: -t[0])
    best = None
    for sc, gva, da, gvb, db, dd in pairs[:6]:  # a CDSE e o Earth Search às vezes discordam de uma data
        ia, ib = item_on(C, da), item_on(C, db)
        if ia and ib:
            best = (sc, gva, ia, gvb, ib, dd); break
    if best is None:
        m["season2"] = {"status": "sem_par", "detail": f"nenhum par limpo com ≤ {MAX_DOY_DIFF} dias de diferença"}
        mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        return m["season2"]["detail"]
    _, gva, ia, gvb, ib, dd = best
    # só vale como "outra estação" se ficou claramente mais verde que o par principal nos dois anos
    gain = [gva - (nda.get(d0[0].isoformat()) or 0), gvb - (ndb.get(d0[1].isoformat()) or 0)]
    prim_ndvi = [nda.get(d0[0].isoformat()), ndb.get(d0[1].isoformat())]
    out = d / "season2"; out.mkdir(exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    x0, y0 = m["crop_selection"]["offset_px"]; S = int(m["crop_selection"]["search_size_m"] / 10)
    G20 = Grid(C.epsg, C.left - x0 * 10, C.top + y0 * 10, S, S, 10.0).at(20.0)
    crops, ctx = [], []
    for it in (ia, ib):
        rr = s2.read_reflectance(it, C, BAND_ORDER); scl = s2.read_scl(it, C)
        crops.append((rr, scl, np.isin(scl, s2.SCL_VALID)))
        ctx.append(s2.read_reflectance(it, G20, ("red", "green", "blue")))
    vb = crops[0][2] & crops[1][2]
    tone = render.pair_tone(crops[0][0], crops[1][0], valid=vb)
    ctx_tone = render.pair_tone(ctx[0], ctx[1])
    zoom = m["display"]["zoom_factor"]; crop = m["aoi"]["shape"][0]
    metas = []
    for (rc, sclc, vc), rctx, it in zip(crops, ctx, (ia, ib)):
        ds = it.datetime.date().isoformat()
        stack = [np.where(np.isfinite(rc[b_]), np.round(rc[b_] * 10000), -32768) for b_ in BAND_ORDER]
        tags = dict(source_item=it.id, source=s2.EARTH_SEARCH, collection=s2.COLLECTION, scale="0.0001", season="oposta")
        save_tif(out / f"{cid}_{ds}_refl10m.tif", stack, C, "int16", -32768, [f"{b_}({s2.BANDS[b_][0]})" for b_ in BAND_ORDER], tags)
        save_tif(out / f"{cid}_{ds}_scl10m.tif", [sclc], C, "uint8", 0, ["SCL"], tags)
        render.upscale(render.apply_tone(rc, tone), zoom).save(out / f"game_{ds}.png", optimize=True)
        cimg = Image.fromarray(render.apply_tone(rctx, ctx_tone))
        ImageDraw.Draw(cimg).rectangle([x0 // 2, y0 // 2, (x0 + crop) // 2 - 1, (y0 + crop) // 2 - 1], outline=(255, 214, 0), width=2)
        cimg.save(out / f"context_{ds}.png", optimize=True)
        meta = s2.item_summary(it)
        meta["crop_valid_fraction_scl"] = round(float(vc.mean()), 4)
        meta["cdse_product_id"] = s2.find_cdse_id(it)
        clon, clat = m["center_lonlat"]
        meta["copernicus_browser_url"] = s2.cdse_browser_url(clon, clat, it.datetime.date(), zoom=14)
        metas.append(meta)
    m["season2"] = {"status": "ok", "images": metas, "doy_difference_days": dd,
                    "ndvi_gain_vs_primary": [round(g, 3) for g in gain],
                    "ndvi_crop": {"season2": [round(gva, 3), round(gvb, 3)],
                                  "primary": [round(x, 3) if x is not None else None for x in prim_ndvi]},
                    "rule": "par mais verde em comum: entre datas limpas (cobertura 100%, SCL válido ≥ 99,9%, névoa ≤ 0,006, s2cloudless ≤ 0,2%) do mesmo ano civil, a ≥ 45 dias da data principal e com ≤ 30 dias de diferença de dia do ano entre os anos, maximiza o menor NDVI médio do recorte",
                    "display_tone": tone}
    mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    return (f"ok {metas[0]['datetime_utc'][:10]} / {metas[1]['datetime_utc'][:10]} (Δdia {dd}) "
            f"NDVI principal {prim_ndvi} → verde {gva:.2f}/{gvb:.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*"); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for mp in sorted((ROOT / "data" / "pairs").glob("*/metadata.json")):
        cid = mp.parent.name
        if a.only and cid not in a.only:
            continue
        try:
            print(cid, build(mp.parent, a.force), flush=True)
        except Exception as e:  # noqa: BLE001
            import traceback; traceback.print_exc(); print(cid, "ERRO", repr(e)[:200], flush=True)
