"""Modelo de DUAS ESTAÇÕES (rf_native_v2): para cada ano, o pixel é descrito pela foto principal (seca)
E pela foto da outra estação (season2/, ver build_season2.py) — a mesma informação que o jogador vê no botão ESTAÇÃO.

Motivação: com uma foto só, mata caducifólia na seca parece pasto (ex.: CAA-03, Seridó: v1 −16,7 pp × MapBiomas −2,5 pp).
O MapBiomas classifica com o ano inteiro; aqui o modelo ganha a segunda estação, e só ela (o jogador vê as mesmas imagens).

Features por ano: 17 da foto principal + 17 da outra estação + ΔNDVI e ΔNDMI entre estações + bioma (6) = 42.
Validação: GroupKFold espacial por desafio (out-of-fold), igual ao v1; compara v1 × v2 nos MESMOS desafios.
Só entram desafios com season2 "ok". Uso: python train_rf2.py [--no-write-metadata]"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_rf import BANDS, BIOMES, NAMES as NAMES_V1, PILOT_BIOME, features, with_biome  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASE = NAMES_V1[:17]
NAMES = [f"seca_{n}" for n in BASE] + [f"chuva_{n}" for n in BASE] + ["dNDVI", "dNDMI"] + [f"bioma_{b}" for b in BIOMES]


def year_features(p1, p2):
    (F1, v1), (F2, v2) = features(p1), features(p2)
    i_ndvi, i_ndmi = BASE.index("NDVI"), BASE.index("NDMI")
    d = np.stack([F2[:, i_ndvi] - F1[:, i_ndvi], F2[:, i_ndmi] - F1[:, i_ndmi]], 1)
    return np.hstack([F1, F2, d]), v1 & v2


def load(d):
    m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    cid = m["challenge_id"]
    lab = d / f"{cid}_labels10m.tif"
    r1 = sorted(d.glob(f"{cid}_*_refl10m.tif")); r2 = sorted((d / "season2").glob(f"{cid}_*_refl10m.tif"))
    if not lab.exists() or len(r1) != 2 or len(r2) != 2 or (m.get("season2") or {}).get("status") != "ok":
        return None
    import rasterio
    with rasterio.open(lab) as src:
        L = src.read()
    (Fa, va), (Fb, vb) = year_features(r1[0], r2[0]), year_features(r1[1], r2[1])
    biome = m.get("biome") or PILOT_BIOME.get(cid, "")
    return dict(id=cid, meta=m, Fa=with_biome(Fa, biome), Fb=with_biome(Fb, biome), ya=L[0].ravel(), yb=L[1].ravel(),
                ra=L[2].ravel(), rb=L[3].ravel(), valid=va & vb)


def sample(c, n, rng):
    X, y = [], []
    for F, lab in ((c["Fa"], c["ya"]), (c["Fb"], c["yb"])):
        ix = np.flatnonzero(c["valid"]); ix = rng.choice(ix, min(n, ix.size), replace=False)
        X.append(F[ix]); y.append(lab[ix])
    return np.vstack(X), np.concatenate(y)


def predict_delta(rf, c):
    v = c["valid"]; pa = rf.predict(c["Fa"][v]); pb = rf.predict(c["Fb"][v])
    return dict(pred_a=100 * pa.mean(), pred_b=100 * pb.mean(), delta_pred=100 * (pb.mean() - pa.mean()),
                delta_ref10=100 * (c["yb"][v].mean() - c["ya"][v].mean()),
                delta_ref30=100 * (c["rb"][v].mean() - c["ra"][v].mean()),
                yt=np.concatenate([c["ya"][v], c["yb"][v]]), yp=np.concatenate([pa, pb]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=5); ap.add_argument("--per-image", type=int, default=3000)
    ap.add_argument("--trees", type=int, default=300); ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-write-metadata", action="store_true")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    dirs = sorted(p.parent for p in (ROOT / "data" / "pairs").glob("*/metadata.json"))
    data = [c for c in (load(d) for d in dirs) if c]
    alias = {"PILOTO-01-PERDA": "CAP-RO", "PILOTO-02-ARMADILHA-PLANTADA": "CER-01", "PILOTO-03-ESTAVEL": "CAP-AM"}
    groups = np.array([alias.get(c["id"], c["id"]) for c in data]); ug = np.unique(groups)
    print(f"{len(data)} desafios com 2 estações ({len(ug)} áreas)")
    fold_of = {g: i % a.folds for i, g in enumerate(rng.permutation(ug))}
    rf_kw = dict(n_estimators=a.trees, min_samples_leaf=3, max_features="sqrt",
                 class_weight="balanced_subsample", n_jobs=-1, random_state=a.seed)
    rows, YT, YP = [], [], []
    for k in range(a.folds):
        tr = [c for c, g in zip(data, groups) if fold_of[g] != k]; te = [c for c, g in zip(data, groups) if fold_of[g] == k]
        if not te:
            continue
        parts = [sample(c, a.per_image, rng) for c in tr]
        rf = RandomForestClassifier(**rf_kw).fit(np.vstack([p[0] for p in parts]), np.concatenate([p[1] for p in parts]))
        for c in te:
            r = predict_delta(rf, c); YT.append(r.pop("yt")); YP.append(r.pop("yp"))
            v1 = (c["meta"].get("model_estimate_v1") or c["meta"].get("model_estimate") or {}).get("delta_pp")
            rows.append(dict(id=c["id"], fold=k, mode=c["meta"]["mode"], biome=c["meta"].get("biome", ""),
                             v1_delta=v1, **{kk: round(float(v), 2) for kk, v in r.items()}))
        print(f"fold {k}: {len(tr)} treino / {len(te)} teste")

    e10 = np.array([r["delta_pred"] - r["delta_ref10"] for r in rows])
    e1 = np.array([r["v1_delta"] - r["delta_ref10"] for r in rows if r["v1_delta"] is not None])
    yt, yp = np.concatenate(YT), np.concatenate(YP)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "model": "rf_native_v2 (duas estações)",
        "n_challenges": len(rows), "n_groups": int(len(ug)), "folds": a.folds,
        "validation": "GroupKFold espacial por desafio (out-of-fold)", "rf_params": rf_kw, "features": NAMES,
        "pixel": {"overall_accuracy": round(float(accuracy_score(yt, yp)), 4), "f1_native": round(float(f1_score(yt, yp)), 4)},
        "delta_vs_mapbiomas10m": {"MAE_pp": round(float(np.abs(e10).mean()), 2), "bias_pp": round(float(e10.mean()), 2),
                                  "RMSE_pp": round(float(np.sqrt((e10 ** 2).mean())), 2),
                                  "n_gap_gt_7_9": int((np.abs(e10) > 7.9).sum())},
        "v1_same_challenges": {"MAE_pp": round(float(np.abs(e1).mean()), 2), "n": int(e1.size),
                               "n_gap_gt_7_9": int((np.abs(e1) > 7.9).sum())},
        "note": "MapBiomas é referência, não verdade absoluta. v1 nos mesmos desafios para comparação direta.",
    }
    out = ROOT / "data" / "model"; out.mkdir(parents=True, exist_ok=True)
    (out / "cv_report_v2.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out / "cv_challenges_v2.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    parts = [sample(c, a.per_image, rng) for c in data]
    final = RandomForestClassifier(**rf_kw).fit(np.vstack([p[0] for p in parts]), np.concatenate([p[1] for p in parts]))
    joblib.dump({"model": final, "features": NAMES, "report": report}, ROOT / "models" / "rf_native_v2.joblib", compress=3)
    if not a.no_write_metadata:
        for r in rows:
            mp = ROOT / "data" / "pairs" / r["id"] / "metadata.json"
            m = json.loads(mp.read_text(encoding="utf-8"))
            if (m.get("model_estimate") or {}).get("model") == "rf_native_v1":
                m["model_estimate_v1"] = m["model_estimate"]
            m["model_estimate"] = {"model": "rf_native_v2", "method": "out-of-fold (GroupKFold espacial), duas estações por ano",
                                   "fold": r["fold"], "native_pct_a": r["pred_a"], "native_pct_b": r["pred_b"],
                                   "delta_pp": r["delta_pred"], "computed_utc": report["generated_utc"]}
            mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("pixel", "delta_vs_mapbiomas10m", "v1_same_challenges")}, indent=1))


if __name__ == "__main__":
    main()
