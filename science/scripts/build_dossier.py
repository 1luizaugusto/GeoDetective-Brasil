"""Dossiê de evidências por desafio: cada afirmação com veredito, o PORQUÊ e as FONTES.

Afirmações automáticas (dados, sempre reprodutíveis):
  tipo de mudança  — MapBiomas 30 m (Col. 11) e 10 m (Col. 4) + NDVI das imagens (data/qa/auditoria_desafios.csv)
  destino/origem   — classes para onde foi a vegetação perdida / de onde veio o ganho (legenda oficial)
  plantio          — silvicultura nos dois mapas
  fogo             — MapBiomas Fogo (Col. 5.1, área queimada anual) no ano das imagens e no anterior
  áreas protegidas — WDPA / Protected Planet (UNEP-WCMC), com % do recorte
  local e bioma    — IBGE (malhas municipais; biomas 1:250 mil)
Afirmações de contexto (história, eventos): data/catalog/context_claims.json, escritas à mão SÓ com fonte verificada;
o que não tem fonte fica marcado como "não comprovado" e sai do texto do jogo.
Saída: data/dossie/<ID>.json (o export_game.py embute no challenges.json).
Uso: python build_dossier.py [--ids ID ...]"""
import argparse
import csv
import json
import sys
from pathlib import Path

import ee
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodet import gee  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = {  # URLs conferidas (HTTP 200) em 2026-11-13
    "mb30": {"nome": "MapBiomas Brasil — Coleção 11, cobertura e uso da terra (30 m, Landsat)",
             "url": "https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/cobertura-30m/cobertura/"},
    "mb10": {"nome": "MapBiomas Brasil — Coleção 4, cobertura 10 m (Sentinel-2)",
             "url": "https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/cobertura-10m/cobertura/"},
    "legenda": {"nome": "MapBiomas — códigos de legenda", "url": "https://brasil.mapbiomas.org/downloads/codigos-de-legenda/"},
    "fogo": {"nome": "MapBiomas Fogo — mapeamento anual de área queimada (Col. 5.1)",
             "url": "https://brasil.mapbiomas.org/iniciativas-e-produtos/fogo/mapeamento-anual/anual/"},
    "gee": {"nome": "MapBiomas — assets no Google Earth Engine (dados usados)",
            "url": "https://brasil.mapbiomas.org/downloads/assets-no-google-earth-engine/"},
    "ibge_biomas": {"nome": "IBGE — Biomas (1:250.000)",
                    "url": "https://www.ibge.gov.br/geociencias/informacoes-ambientais/estudos-ambientais/15842-biomas.html"},
    "sentinel_legal": {"nome": "Copernicus Sentinel Data — aviso legal",
                       "url": "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"},
}


def src(*keys):
    return [SRC[k] for k in keys]


def protected_areas(bbox):
    w, s, e, n = bbox
    poly = ee.Geometry.Rectangle([w, s, e, n], None, False)
    fc = ee.FeatureCollection("WCMC/WDPA/current/polygons").filterBounds(poly.buffer(1000))
    fc = fc.map(lambda f: f.set("frac", f.geometry().intersection(poly, 10).area(10).divide(poly.area(10))))
    out = []
    for f in fc.limit(20).getInfo()["features"]:
        p = f["properties"]
        out.append({"nome": p.get("NAME"), "tipo": p.get("DESIG"), "ano": p.get("STATUS_YR"),
                    "site_id": p.get("SITE_ID") or p.get("WDPAID"), "frac": float(p.get("frac") or 0)})
    return sorted(out, key=lambda r: -r["frac"])


def fire(m):
    l, b, r, t = m["aoi"]["bounds_utm"]; h, w = m["aoi"]["shape"]
    ya, yb = m["years"]
    f = ee.Image(gee.ASSETS["fire_annual_c51"])
    years = sorted({ya - 1, ya, yb - 1, yb})
    bands = [f.select(f"burned_area_{y}").gt(0).unmask(0).rename(f"y{y}") for y in years]
    arr = ee.data.computePixels({"expression": ee.Image.cat(bands).toUint8(), "fileFormat": "NUMPY_NDARRAY",
        "grid": {"dimensions": {"width": w, "height": h},
                 "affineTransform": {"scaleX": 10, "shearX": 0, "translateX": l, "shearY": 0, "scaleY": -10, "translateY": t},
                 "crsCode": m["aoi"]["crs"]}})
    return {y: round(100 * float(np.asarray(arr[f"y{y}"]).mean()), 1) for y in years}


def fnum(x):
    return f"{float(x):+.1f}".replace(".", ",")


def fnum2(x):
    return f"{float(x):.2f}".replace(".", ",")


def br(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


# tolerância de pontuação = MAE do modelo de duas épocas (mesma regra do export_game.py)
_cv2 = ROOT / "data" / "model" / "cv_report_v2.json"
TOL = round(min(10.0, max(3.0, json.loads(_cv2.read_text(encoding="utf-8"))["delta_vs_mapbiomas10m"]["MAE_pp"])), 1) if _cv2.exists() else 7.9


def build(cid, aud, ctx, qa):
    d = ROOT / "data" / "pairs" / cid
    m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    ya, yb = m["years"]
    imgs = [{"nome": f"Sentinel-2 L2A {im['datetime_utc'][:10]} — {im.get('cdse_product_id') or im['earth_search_id']}",
             "url": im.get("copernicus_browser_url") or SRC["sentinel_legal"]["url"]} for im in m["images"]]
    A = aud
    p10, g10, p30, g30 = (float(A[k]) for k in ("perda_10m_pp", "ganho_10m_pp", "perda_30m_pp", "ganho_30m_pp"))
    net10, net30 = g10 - p10, g30 - p30
    kind = qa.get("kind_override", m["mode"])
    claims = []

    # 1) tipo de mudança — o centro do desafio
    ndvi = A.get("ndvi_mediana", "")
    numbers = (f"MapBiomas 10 m: perda {p10:.1f} pp e ganho {g10:.1f} pp (líquido {fnum(net10)} pp); "
               f"MapBiomas 30 m: perda {p30:.1f} pp e ganho {g30:.1f} pp (líquido {fnum(net30)} pp). "
               f"NDVI mediano das imagens: {ndvi}.")
    if kind == "loss":
        dn = A.get("dNDVI_perda", "")
        claims.append({"afirmacao": f"Houve perda de vegetação nativa entre {ya} e {yb}.", "veredito": "comprovado",
                       "porque": numbers + (f" Nos pixels que os dois mapas marcam como perda, o NDVI variou {dn} (vegetação a menos)." if dn else ""),
                       "fontes": src("mb30", "mb10") + imgs})
    elif kind == "gain":
        dg = A.get("dNDVI_ganho", "")
        claims.append({"afirmacao": f"Houve ganho (regeneração) de vegetação nativa entre {ya} e {yb}.", "veredito": "comprovado",
                       "porque": numbers + (f" Nos pixels que os dois mapas marcam como ganho, o NDVI subiu {dg}." if dg else ""),
                       "fontes": src("mb30", "mb10") + imgs})
    elif kind == "trap":
        claims.append({"afirmacao": "A mudança líquida de vegetação nativa é próxima de zero (armadilha).", "veredito": "comprovado",
                       "porque": numbers + " A imagem muda bastante, mas os mapas não registram troca de vegetação nativa.",
                       "fontes": src("mb30", "mb10") + imgs})
    else:
        claims.append({"afirmacao": f"A vegetação nativa ficou praticamente estável entre {ya} e {yb}.", "veredito": "comprovado",
                       "porque": numbers + " Mudanças de cor (estação, safra, água, fogo) não contam como troca de vegetação.",
                       "fontes": src("mb30", "mb10") + imgs})
    if qa.get("audit_override"):
        claims[-1]["revisao"] = "Revisão manual: " + qa["audit_override"]

    # 1b) JUSTIÇA: duas épocas por ano + gabarito (modelo) concorda com a referência (MapBiomas)
    s2m = m.get("season2") or {}
    if s2m.get("status") == "ok":
        d1 = [im["datetime_utc"][:10] for im in m["images"]]; d2 = [im["datetime_utc"][:10] for im in s2m["images"]]
        n1 = s2m["ndvi_crop"]["primary"]; n2 = s2m["ndvi_crop"]["season2"]
        txt = (f"Época 1: {br(d1[0])} e {br(d1[1])} ({m['doy_difference_days']} dia{'' if m['doy_difference_days'] == 1 else 's'} de diferença no calendário). "
               f"Época 2: {br(d2[0])} e {br(d2[1])} ({s2m['doy_difference_days']} dia{'' if s2m['doy_difference_days'] == 1 else 's'}), a data mais verde que os dois anos "
               f"têm na mesma época, sem nuvem no recorte. NDVI médio do recorte: época 1 {fnum2(n1[0])} → {fnum2(n1[1])}; "
               f"época 2 {fnum2(n2[0])} → {fnum2(n2[1])}.")
        if abs(n2[0] - n2[1]) > 0.08:
            txt += (f" Na época 2, {ya if n2[0] > n2[1] else yb} está mais verde no recorte inteiro: essa diferença de cor "
                    "vem do momento da foto (chuva, rebrota), e por isso o gabarito vem dos mapas e do modelo, não da cor.")
        claims.append({"afirmacao": "As duas fotos de cada ano são da mesma época, e há uma segunda época para comparar.",
                       "veredito": "comprovado", "porque": txt,
                       "fontes": imgs + [{"nome": f"Sentinel-2 L2A {im['datetime_utc'][:10]} — {im.get('cdse_product_id') or im['earth_search_id']}",
                                          "url": im.get("copernicus_browser_url") or SRC["sentinel_legal"]["url"]} for im in s2m["images"]]})
    me = m.get("model_estimate") or {}
    if me.get("model") == "rf_native_v2":
        gap = abs(me["delta_pp"] - net10)
        claims.append({"afirmacao": "O gabarito do jogo (modelo) concorda com o MapBiomas.",
                       "veredito": "comprovado" if gap <= TOL else "não comprovado",
                       "porque": (f"Modelo de duas épocas: {fnum(me['delta_pp'])} pp; MapBiomas 10 m: {fnum(net10)} pp; "
                                  f"diferença {gap:.1f} pp, {'dentro' if gap <= TOL else 'FORA'} da tolerância de pontuação ({TOL:.1f} pp). "
                                  "O modelo vê só as imagens deste caso (as duas épocas de cada ano) e foi testado em áreas "
                                  "que não usou no treino (validação espacial)."),
                       "fontes": src("mb10")})

    # 2) para onde foi / de onde veio
    if min(p10, p30) >= 1:
        claims.append({"afirmacao": "Destino da vegetação nativa perdida.", "veredito": "comprovado",
                       "porque": f"Mapa 10 m: {A['perda_virou_10m']}. Mapa 30 m: {A['perda_virou_30m']}.",
                       "fontes": src("mb10", "mb30", "legenda")})
    if min(g10, g30) >= 1:
        claims.append({"afirmacao": "Origem da vegetação nativa ganha.", "veredito": "comprovado",
                       "porque": f"Mapa 10 m: {A['ganho_veio_de_10m']}. Mapa 30 m: {A['ganho_veio_de_30m']}.",
                       "fontes": src("mb10", "mb30", "legenda")})

    # 3) plantio comercial (silvicultura ≠ nativa)
    s10, s30 = float(A["silv_ganho_10m_pp"]), float(A["silv_ganho_30m_pp"])
    if min(s10, s30) >= 20:
        dp = A.get("dNDVI_plantio", "")
        claims.append({"afirmacao": "O verde novo é plantio comercial (silvicultura), não vegetação nativa.", "veredito": "comprovado",
                       "porque": f"Silvicultura no mapa 10 m: {A['silv_10m']}; no mapa 30 m: {A['silv_30m']}."
                                 + (f" NDVI nos pixels de plantio novo: {float(dp):+.2f} (dossel de árvores)." if dp != "" else ""),
                       "fontes": src("mb10", "mb30", "legenda") + imgs})
    elif max(s10, s30) >= 5:  # os mapas discordam no tamanho do plantio: dizer exatamente o que cada um mostra
        dp = A.get("dNDVI_plantio", "")
        claims.append({"afirmacao": "Houve plantio comercial novo (silvicultura), em tamanho diferente em cada mapa.", "veredito": "comprovado",
                       "porque": f"Silvicultura no mapa 10 m: {A['silv_10m']}; no mapa 30 m: {A['silv_30m']}. "
                                 "Onde o mapa de 30 m marca plantio, o de 10 m marca sobretudo mosaico de usos e pastagem; "
                                 "nos dois mapas, nada disso é vegetação nativa."
                                 + (f" NDVI nos pixels de plantio novo: {float(dp):+.2f}." if dp != "" else ""),
                       "fontes": src("mb10", "mb30", "legenda") + imgs})
    else:
        claims.append({"afirmacao": "Não houve expansão de plantio comercial (silvicultura).", "veredito": "comprovado",
                       "porque": f"Silvicultura no mapa 10 m: {A['silv_10m']}; no mapa 30 m: {A['silv_30m']}.",
                       "fontes": src("mb10", "mb30")})

    # 4) fogo
    fz = fire(m)
    burned = {y: v for y, v in fz.items() if v >= 5}
    if burned:
        txt = "; ".join(f"{y}: {v:.0f}% do recorte".replace(".", ",") for y, v in sorted(burned.items()))
        claims.append({"afirmacao": "Houve fogo registrado no recorte.", "veredito": "comprovado",
                       "porque": f"Área queimada (MapBiomas Fogo): {txt}. Fogo muda a cor da imagem; vegetação nativa queimada continua nativa.",
                       "fontes": src("fogo")})
    else:
        claims.append({"afirmacao": "Não houve fogo relevante no recorte.", "veredito": "comprovado",
                       "porque": "MapBiomas Fogo: " + "; ".join(f"{y}: {v:.0f}%" for y, v in sorted(fz.items())) + " do recorte queimado.",
                       "fontes": src("fogo")})

    # 5) áreas protegidas (WDPA)
    pas = [p for p in protected_areas(m["aoi"]["bbox_lonlat"]) if p["frac"] > 0.005 or p["frac"] == 0]
    for p in pas[:4]:
        rel = f"cobre {100 * p['frac']:.0f}% do recorte".replace(".", ",") if p["frac"] > 0.005 else "fica a menos de 1 km do recorte"
        claims.append({"afirmacao": f"Área protegida: {p['nome']} ({p['tipo']}{', criada em ' + str(p['ano']) if p['ano'] else ''}).",
                       "veredito": "comprovado", "porque": f"Segundo a base mundial de áreas protegidas (WDPA), ela {rel}.",
                       "fontes": [{"nome": "Protected Planet / WDPA (UNEP-WCMC)",
                                   "url": f"https://www.protectedplanet.net/{p['site_id']}" if p["site_id"] else "https://www.protectedplanet.net/"}]})

    # 6) local e bioma
    ver = m.get("verification", {}).get("ibge_location_of_center") or {}
    if ver:
        claims.append({"afirmacao": f"O centro do recorte fica em {ver['municipio']}/{ver['uf']}, bioma {m.get('biome', '')}.",
                       "veredito": "comprovado", "porque": f"Malha municipal oficial do IBGE (código {ver['ibge_municipio_codigo']}) e mapa de biomas do IBGE.",
                       "fontes": [{"nome": f"IBGE — município {ver['ibge_municipio_codigo']}",
                                   "url": f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{ver['ibge_municipio_codigo']}"},
                                  SRC["ibge_biomas"]]})

    # 7) contexto (curado, com fonte) — inclusive o que foi REMOVIDO por falta de prova
    for c in ctx:
        claims.append(c)
    return {"id": cid, "gerado": "build_dossier.py", "afirmacoes": claims, "fire_pct": fz,
            "areas_protegidas": pas}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ids", nargs="*"); a = ap.parse_args()
    gee.init("geodetective-brasil")
    aud = {r["id"]: r for r in csv.DictReader((ROOT / "data" / "qa" / "auditoria_desafios.csv").open(encoding="utf-8"))}
    qa = json.loads((ROOT / "data" / "catalog" / "qa_decisions.json").read_text(encoding="utf-8"))
    cp = ROOT / "data" / "catalog" / "context_claims.json"
    ctx = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {}
    ids = a.ids or [c["id"] for c in json.loads((ROOT / "game" / "public" / "data" / "challenges.json").read_text(encoding="utf-8"))["challenges"]]
    out = ROOT / "data" / "dossie"; out.mkdir(parents=True, exist_ok=True)
    for cid in ids:
        dz = build(cid, aud[cid], ctx.get(cid, []), qa.get(cid, {}))
        (out / f"{cid}.json").write_text(json.dumps(dz, indent=1, ensure_ascii=False), encoding="utf-8")
        pa = "; ".join(f"{p['nome']} {100*p['frac']:.0f}%" for p in dz["areas_protegidas"][:3])
        print(f"{cid}: {len(dz['afirmacoes'])} afirmações | fogo {dz['fire_pct']} | AP: {pa}", flush=True)


if __name__ == "__main__":
    main()
