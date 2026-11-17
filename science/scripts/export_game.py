"""Exporta o contrato científico → jogo: data/game/challenges.json + imagens WebP.

Entram só os desafios APROVADOS no QA visual (data/catalog/qa_decisions.json: {id: {"status", "note"}}),
a menos que --all. O jogo nunca roda ML: tudo aqui é pré-calculado.

Tolerância de pontuação (docs 7.3) = incerteza do modelo = MAE do Δ na validação espacial
(data/model/cv_report.json), limitada a [3, 10] pp.
Uso: python export_game.py [--all] [--out data/game]"""
import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "1.0"

ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true"); ap.add_argument("--out", default=str(ROOT / "game" / "public" / "data"))
ap.add_argument("--quality", type=int, default=85)
ap.add_argument("--max-gap", type=float, default=None,
                help="máx. |Δ modelo − Δ MapBiomas 10 m| para entrar no jogo (padrão: a própria tolerância de pontuação)")
a = ap.parse_args()
out = Path(a.out); img_dir = out / "img"
if img_dir.exists():
    shutil.rmtree(img_dir)
img_dir.mkdir(parents=True)

qa_path = ROOT / "data" / "catalog" / "qa_decisions.json"
qa = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.exists() else {}
import csv  # noqa: E402
aud_path = ROOT / "data" / "qa" / "auditoria_desafios.csv"
audit = {r["id"]: r for r in csv.DictReader(aud_path.open(encoding="utf-8"))} if aud_path.exists() else {}
# modelo de DUAS ESTAÇÕES (train_rf2.py): vê seca + chuva de cada ano, as mesmas imagens do botão ESTAÇÃO
cv = json.loads((ROOT / "data" / "model" / "cv_report_v2.json").read_text(encoding="utf-8"))
MODEL = "rf_native_v2"
mae = cv["delta_vs_mapbiomas10m"]["MAE_pp"]
tol = round(min(10.0, max(3.0, mae)), 1)
# JUSTIÇA: o gabarito (modelo) e a referência (MapBiomas) têm de concordar dentro da tolerância;
# se discordam, o jogador acertaria "o certo" e perderia pontos — o caso fica fora
max_gap = a.max_gap if a.max_gap is not None else tol
# FAIXA DE 100 PONTOS por caso: do valor do modelo ao do MapBiomas (os dois são medições aceitáveis),
# com margem de 3 pp (o piso da regra de tolerância). Fora da faixa, os pontos caem até zero em 40 pp.
MARGIN = 3.0


def webp(src, dst, size=None):
    im = Image.open(src).convert("RGB")
    if size:
        im = im.resize((size, size), Image.LANCZOS)
    im.save(dst, "WEBP", quality=a.quality, method=6)
    return f"data/img/{dst.name}"


items, skipped = [], []
for mp in sorted((ROOT / "data" / "pairs").glob("*/metadata.json")):
    m = json.loads(mp.read_text(encoding="utf-8")); cid = m["challenge_id"]
    if cid.startswith("PILOTO"):
        continue  # pilotos são duplicatas de CER-01 / CAP-AM / CAP-RO
    dec = qa.get(cid, {}).get("status")
    if not a.all and dec != "aprovado":
        skipped.append((cid, dec or "sem QA")); continue
    s2m = m.get("season2") or {}
    if not a.all and s2m.get("status") != "ok":
        skipped.append((cid, "sem par limpo da outra estação")); continue
    if not m.get("model_estimate") or (not a.all and m["model_estimate"].get("model") != MODEL):
        skipped.append((cid, f"sem estimativa {MODEL}")); continue
    ref = m["reference_mapbiomas"]
    gap = abs(m["model_estimate"]["delta_pp"] - ref["delta_pp_10m"])
    if not a.all and gap > max_gap:  # jogo justo: o gabarito (modelo) precisa concordar com a referência
        skipped.append((cid, f"modelo×MapBiomas divergem {gap:.0f} pp")); continue
    # auditoria (audit_challenges.py): o tipo de mudança precisa estar comprovado pelos dois mapas + NDVI,
    # ou revisado à mão com motivo registrado em qa_decisions[cid]["audit_override"]
    aud = audit.get(cid)
    if not a.all and (aud is None or (aud["veredito"] != "OK" and not qa.get(cid, {}).get("audit_override"))):
        skipped.append((cid, "auditoria: " + ("não auditado" if aud is None else aud.get("alertas", "REVISAR")))); continue
    d = mp.parent; ims = m["images"]; ya, yb = m["years"]
    dates = [im["datetime_utc"][:10] for im in ims]
    dates2 = [im["datetime_utc"][:10] for im in s2m["images"]] if s2m.get("status") == "ok" else None
    ver = m.get("verification", {}).get("ibge_location_of_center") or {}
    name = re.sub(r",\s*[^,]+/[A-Z]{2}$", "", m["name"])  # "Local, Município/UF" → "Local" (UF vai à parte)
    name = qa.get(cid, {}).get("name_override", name)  # nome revisado (apply_context_review.py)
    dz_path = ROOT / "data" / "dossie" / f"{cid}.json"  # build_dossier.py: afirmações + veredito + porquê + fontes
    dossier = json.loads(dz_path.read_text(encoding="utf-8"))["afirmacoes"] if dz_path.exists() else []
    # só o que está comprovado vai ao jogador; o histórico de correções fica em context_claims.json
    dossier = [cl for cl in dossier if cl.get("veredito") == "comprovado"]
    for cl in dossier:  # números em pt-BR (vírgula decimal) para o jogador
        cl["porque"] = re.sub(r"(\d)\.(\d)", r"\1,\2", cl["porque"])
    if not a.all and not dossier:
        skipped.append((cid, "sem dossiê de evidências (build_dossier.py)")); continue
    items.append({
        "id": cid, "name": name, "group": m.get("group", ""), "biome": m.get("biome", ""),
        "uf": ver.get("uf"), "municipality": ver.get("municipio"),
        "center_lonlat": m["center_lonlat"], "bbox_lonlat": m["aoi"]["bbox_lonlat"],
        "size_km": m["aoi"]["size_m"] / 1000, "pixel_m": 10,
        "dates": dates, "years": [ya, yb],
        "images": {
            "before": webp(d / f"game_{dates[0]}.png", img_dir / f"{cid}_{ya}.webp"),
            "after": webp(d / f"game_{dates[1]}.png", img_dir / f"{cid}_{yb}.webp"),
            "context_before": webp(d / f"context_{dates[0]}.png", img_dir / f"{cid}_{ya}_ctx.webp"),
            "context_after": webp(d / f"context_{dates[1]}.png", img_dir / f"{cid}_{yb}_ctx.webp"),
            **({"before2": webp(d / "season2" / f"game_{dates2[0]}.png", img_dir / f"{cid}_{ya}_s2.webp"),
                "after2": webp(d / "season2" / f"game_{dates2[1]}.png", img_dir / f"{cid}_{yb}_s2.webp"),
                "context_before2": webp(d / "season2" / f"context_{dates2[0]}.png", img_dir / f"{cid}_{ya}_s2_ctx.webp"),
                "context_after2": webp(d / "season2" / f"context_{dates2[1]}.png", img_dir / f"{cid}_{yb}_s2_ctx.webp")}
               if dates2 else {}),
        },
        "dates2": dates2,
        # aviso de época: só quando os DADOS mostram que a época 1 é bem menos verde nos dois anos (ΔNDVI > 0,10)
        "season_hint": bool(dates2 and min(s2m.get("ndvi_gain_vs_primary") or [0]) > 0.10),
        "products": [{"id": im.get("cdse_product_id") or im["earth_search_id"],
                      "browser_url": im.get("copernicus_browser_url")} for im in ims + (s2m.get("images") or [])],
        "model_estimate_pp": round(m["model_estimate"]["delta_pp"], 1),
        "model_uncertainty_pp": tol,
        "score_band": [round(min(m["model_estimate"]["delta_pp"], ref["delta_pp_10m"]) - MARGIN, 1),
                       round(max(m["model_estimate"]["delta_pp"], ref["delta_pp_10m"]) + MARGIN, 1)],
        "reference_pp": {"mapbiomas_10m": ref["delta_pp_10m"], "mapbiomas_30m": ref["delta_pp_30m"]},
        "native_pct": {"model": [round(m["model_estimate"]["native_pct_a"], 1), round(m["model_estimate"]["native_pct_b"], 1)],
                       "mapbiomas_10m": [ref[f"native_pct_10m_{ya}"], ref[f"native_pct_10m_{yb}"]]},
        "kind": qa.get(cid, {}).get("kind_override", m["mode"]),  # tipo comprovado na auditoria
        "hypothesis": m.get("selection_hypothesis", ""),
        "explanation": qa.get(cid, {}).get("explanation", ""),
        "qa_note": qa.get(cid, {}).get("player_note", ""),  # "note" é registro técnico do QA; só player_note vai ao jogador
        "dossier": dossier,
        "attribution": m["attribution"],
    })


def campaign_order(items, seed=2026):
    """Ordem da campanha MISTURADA e reprodutível (sorteio fixo):
    - os demais tipos (estável, regeneração, armadilha) ficam espalhados por igual ao longo da campanha;
    - as perdas, que são o tipo mais comum, intercalam com eles (perda, outro, perda, outro...);
    - o 1º caso é uma perda clara (|Δ| ≥ 20 pp), para o jogador entender a mecânica."""
    import random
    rng = random.Random(seed)
    by = {}
    for c in sorted(items, key=lambda c: c["id"]):
        by.setdefault(c["kind"], []).append(c)
    loss = by.pop("loss", []); rng.shuffle(loss)
    pos = []
    for kind, cs in sorted(by.items()):
        rng.shuffle(cs); n = len(cs)
        pos += [((i + rng.uniform(0.2, 0.8)) / n, c) for i, c in enumerate(cs)]
    other = [c for _, c in sorted(pos, key=lambda t: t[0])]
    k = next((k for k, c in enumerate(loss) if abs(c["reference_pp"]["mapbiomas_10m"]) >= 20), 0)
    loss.insert(0, loss.pop(k))
    seq = []
    while loss or other:
        if loss: seq.append(loss.pop(0))
        if other: seq.append(other.pop(0))
    return seq


items = campaign_order(items)
doc = {
    "schema_version": SCHEMA, "generated_utc": datetime.now(timezone.utc).isoformat(),
    "target": "variação líquida da cobertura de vegetação NATIVA (pontos percentuais da área do recorte)",
    "scoring": {"formula": "round(100 * max(0, 1 - distancia_ate_a_faixa / 40)); faixa = [min(modelo, MapBiomas) - 3, max(modelo, MapBiomas) + 3]",
                "margin_pp": MARGIN, "tolerance_pp": tol,
                "source": "faixa de 100 pontos por caso: do modelo ao MapBiomas 10 m, mais 3 pp de margem. "
                          f"Só entram casos em que os dois diferem no máximo {tol:g} pp (erro médio do modelo na validação espacial)."},
    "model": {"name": MODEL, "seasons": "duas imagens por ano: a principal (seca) e a mais verde em comum (chuva)", "validation": cv["validation"], "pixel": cv["pixel"],
              "delta_vs_mapbiomas10m": cv["delta_vs_mapbiomas10m"]},
    "limitations": [
        "A resposta é a estimativa de um modelo (Random Forest), não uma medição de campo.",
        "O MapBiomas é usado como referência independente, mas também tem erros.",
        "Imagens Sentinel-2 com 10 m por pixel, ampliadas ×3 sem super-resolução: detalhes menores que ~20 m não são confiáveis.",
        "Diferenças de estação, seca ou fumaça podem mudar a cor sem mudar a vegetação nativa. Por isso cada ano tem duas imagens (seca e chuva), que o modelo também usa.",
        "O modelo reconhece bem florestas, mas subestima formações abertas nativas (campos, savanas como o lavrado, caatinga, restinga), que parecem pasto. A mudança estimada ainda é confiável nos casos do jogo; a quantidade total de nativa, nem sempre.",
        "Só entram casos em que o modelo e o MapBiomas concordam dentro da tolerância de pontuação; quando discordam, o caso fica fora do jogo.",
    ],
    "licenses": "Contains modified Copernicus Sentinel data (Copernicus Sentinel Data Legal Notice); MapBiomas Brasil (CC-BY 4.0)",
    "challenges": items,
}
(out / "challenges.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"{len(items)} desafios exportados → {out / 'challenges.json'}  (tolerância {tol} pp)")
if skipped:
    print("fora:", skipped)
