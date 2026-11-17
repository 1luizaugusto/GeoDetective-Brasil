"""Random Forest: classifica cada pixel 10 m em nativa / não-nativa (rótulo MapBiomas 10 m Col.4)
e estima o Δ de vegetação nativa (pp) de cada desafio = %nativa(B) − %nativa(A).

Validação ESPACIAL: GroupKFold por desafio (o desafio avaliado nunca contribui pixels ao treino).
A estimativa gravada no jogo (metadata.model_estimate) é a OUT-OF-FOLD — honesta, sem vazamento.
Métricas (substituem o MAPE da proposta, inadequado quando Δ≈0): MAE, viés, RMSE do Δ em pp;
acurácia global e F1 por pixel. Referência: MapBiomas 10 m e, independente, 30 m.

Uso: python train_rf.py [--folds 5] [--per-image 3000] [--trees 300]
Saídas: data/model/cv_report.json, data/model/cv_challenges.csv, data/model/cv_scatter.png,
        models/rf_native_v1.joblib (modelo final, todos os desafios) e metadata.model_estimate."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import rasterio
from scipy.ndimage import uniform_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
BANDS = ["blue", "green", "red", "rededge1", "rededge2", "rededge3", "nir", "nir08", "swir16", "swir22"]


def nd(a, b):
    return (a - b) / (a + b + 1e-6)


def features(path):
    with rasterio.open(path) as src:
        x = src.read().astype("float32")
        bad = (x == -32768).any(0)
    x = np.where(x == -32768, np.nan, x / 10000.0)
    B = dict(zip(BANDS, x))
    idx = [nd(B["nir"], B["red"]), nd(B["nir"], B["swir16"]), nd(B["nir"], B["swir22"]),
           nd(B["green"], B["nir"]), nd(B["rededge3"], B["rededge1"])]
    ndvi = np.nan_to_num(idx[0])
    m = uniform_filter(ndvi, 5); s = np.sqrt(np.maximum(uniform_filter(ndvi ** 2, 5) - m ** 2, 0))
    F = np.stack(list(x) + idx + [m, s]).reshape(17, -1).T
    return F, (~bad).ravel() & np.isfinite(F).all(1)


BIOMES = ["Amazônia", "Caatinga", "Cerrado", "Mata Atlântica", "Pampa", "Pantanal"]
# bioma (IBGE) como variável: "nativo" no Cerrado/Caatinga/Pampa é campo e savana, não floresta
NAMES = BANDS + ["NDVI", "NDMI", "NBR", "NDWI", "RE_ratio", "NDVI_mean5", "NDVI_std5"] + [f"bioma_{b}" for b in BIOMES]
PILOT_BIOME = {"PILOTO-01-PERDA": "Amazônia", "PILOTO-02-ARMADILHA-PLANTADA": "Cerrado", "PILOTO-03-ESTAVEL": "Amazônia"}


def with_biome(F, biome):
    oh = np.zeros((F.shape[0], len(BIOMES)), "float32")
    if biome in BIOMES:
        oh[:, BIOMES.index(biome)] = 1
    return np.hstack([F, oh])


def load(d):
    m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    cid = m["challenge_id"]
    lab = d / f"{cid}_labels10m.tif"
    refl = sorted(d.glob(f"{cid}_*_refl10m.tif"))
    if not lab.exists() or len(refl) != 2:
        return None
    with rasterio.open(lab) as src:
        L = src.read()
    (Fa, va), (Fb, vb) = features(refl[0]), features(refl[1])
    biome = m.get("biome") or PILOT_BIOME.get(cid, "")
    Fa, Fb = with_biome(Fa, biome), with_biome(Fb, biome)
    return dict(id=cid, meta=m, Fa=Fa, Fb=Fb, ya=L[0].ravel(), yb=L[1].ravel(),
                ra=L[2].ravel(), rb=L[3].ravel(), valid=va & vb)


def sample(c, n, rng):
    X, y = [], []
    for F, lab in ((c["Fa"], c["ya"]), (c["Fb"], c["yb"])):
        ix = np.flatnonzero(c["valid"])
        ix = rng.choice(ix, min(n, ix.size), replace=False)
        X.append(F[ix]); y.append(lab[ix])
    return np.vstack(X), np.concatenate(y)


def predict_delta(rf, c):
    v = c["valid"]
    pa = rf.predict(c["Fa"][v]); pb = rf.predict(c["Fb"][v])
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
    # pilotos duplicam CER-01/CAP-AM/CAP-RO → mesma área; ficam no mesmo grupo para não vazar
    alias = {"PILOTO-01-PERDA": "CAP-RO", "PILOTO-02-ARMADILHA-PLANTADA": "CER-01", "PILOTO-03-ESTAVEL": "CAP-AM"}
    groups = np.array([alias.get(c["id"], c["id"]) for c in data])
    ug = np.unique(groups)
    print(f"{len(data)} desafios com rótulos ({len(ug)} áreas independentes)")
    fold_of = {g: i % a.folds for i, g in enumerate(rng.permutation(ug))}
    rf_kw = dict(n_estimators=a.trees, min_samples_leaf=3, max_features="sqrt",
                 class_weight="balanced_subsample", n_jobs=-1, random_state=a.seed)
    rows, YT, YP = [], [], []
    for k in range(a.folds):
        tr = [c for c, g in zip(data, groups) if fold_of[g] != k]
        te = [c for c, g in zip(data, groups) if fold_of[g] == k]
        if not te:
            continue
        parts = [sample(c, a.per_image, rng) for c in tr]
        X = np.vstack([p[0] for p in parts]); y = np.concatenate([p[1] for p in parts])
        rf = RandomForestClassifier(**rf_kw).fit(X, y)
        for c in te:
            r = predict_delta(rf, c)
            YT.append(r.pop("yt")); YP.append(r.pop("yp"))
            rows.append(dict(id=c["id"], fold=k, mode=c["meta"]["mode"], biome=c["meta"].get("biome", ""),
                             **{kk: round(float(v), 2) for kk, v in r.items()}))
        print(f"fold {k}: treino {len(tr)} desafios / {len(y)} px, teste {[c['id'] for c in te]}")

    e10 = np.array([r["delta_pred"] - r["delta_ref10"] for r in rows])
    e30 = np.array([r["delta_pred"] - r["delta_ref30"] for r in rows])
    yt, yp = np.concatenate(YT), np.concatenate(YP)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "n_challenges": len(rows), "n_groups": int(len(ug)), "folds": a.folds,
        "validation": "GroupKFold espacial por desafio (out-of-fold)",
        "rf_params": rf_kw, "features": NAMES, "pixels_per_image_train": a.per_image,
        "pixel": {"overall_accuracy": round(float(accuracy_score(yt, yp)), 4),
                  "f1_native": round(float(f1_score(yt, yp)), 4), "n_pixels": int(yt.size)},
        "delta_vs_mapbiomas10m": {"MAE_pp": round(float(np.abs(e10).mean()), 2), "bias_pp": round(float(e10.mean()), 2),
                                  "RMSE_pp": round(float(np.sqrt((e10 ** 2).mean())), 2),
                                  "pearson_r": round(float(np.corrcoef([r["delta_pred"] for r in rows], [r["delta_ref10"] for r in rows])[0, 1]), 3)},
        "delta_vs_mapbiomas30m": {"MAE_pp": round(float(np.abs(e30).mean()), 2), "bias_pp": round(float(e30.mean()), 2),
                                  "RMSE_pp": round(float(np.sqrt((e30 ** 2).mean())), 2)},
        "note": "MapBiomas é referência, não verdade absoluta. Sem amostra de campo/Olofsson ainda.",
    }
    out = ROOT / "data" / "model"; out.mkdir(parents=True, exist_ok=True)
    (out / "cv_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    import csv
    with open(out / "cv_challenges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot([-100, 100], [-100, 100], color="#888", lw=1)
    ax.scatter([r["delta_ref10"] for r in rows], [r["delta_pred"] for r in rows], s=22)
    ax.set_xlabel("Δ MapBiomas 10 m (pp)"); ax.set_ylabel("Δ Random Forest out-of-fold (pp)")
    ax.set_title(f"MAE {report['delta_vs_mapbiomas10m']['MAE_pp']} pp · n={len(rows)}")
    ax.set_xlim(-100, 100); ax.set_ylim(-100, 100); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(out / "cv_scatter.png", dpi=120)

    # modelo final (todos os desafios) — para uso futuro em desafios NOVOS
    parts = [sample(c, a.per_image, rng) for c in data]
    final = RandomForestClassifier(**rf_kw).fit(np.vstack([p[0] for p in parts]), np.concatenate([p[1] for p in parts]))
    (ROOT / "models").mkdir(exist_ok=True)
    joblib.dump({"model": final, "features": NAMES, "report": report}, ROOT / "models" / "rf_native_v1.joblib", compress=3)

    if not a.no_write_metadata:
        for r in rows:
            mp = ROOT / "data" / "pairs" / r["id"] / "metadata.json"
            m = json.loads(mp.read_text(encoding="utf-8"))
            m["model_estimate"] = {"model": "rf_native_v1", "method": "out-of-fold (GroupKFold espacial)",
                                   "fold": r["fold"], "native_pct_a": r["pred_a"], "native_pct_b": r["pred_b"],
                                   "delta_pp": r["delta_pred"], "computed_utc": report["generated_utc"]}
            mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("pixel", "delta_vs_mapbiomas10m", "delta_vs_mapbiomas30m")}, indent=1))


if __name__ == "__main__":
    main()
