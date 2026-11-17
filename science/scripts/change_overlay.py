"""Folha de evidência visual: imagens do jogo (antes/depois) + pixels onde OS DOIS mapas MapBiomas
(10 m Col. 4 e 30 m Col. 11) concordam em perda (vermelho) ou ganho (verde) de vegetação nativa,
e em plantio novo de silvicultura (amarelo). Serve para conferir a olho se a mudança dos mapas aparece na imagem.
Saída: data/qa/evidencia_<nome>.png
Uso: python change_overlay.py ID [ID ...] [--name NOME]"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_challenges import NAT, classes_on_grid  # noqa: E402
from geodet import gee  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(); ap.add_argument("ids", nargs="+"); ap.add_argument("--name", default="revisao")
a = ap.parse_args()
gee.init("geodetective-brasil")
import json  # noqa: E402

T = 360
rows = []
for cid in a.ids:
    d = ROOT / "data" / "pairs" / cid
    m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    C = classes_on_grid(m)
    na10, nb10 = np.isin(C["c10a"], list(NAT)), np.isin(C["c10b"], list(NAT))
    na30, nb30 = np.isin(C["c30a"], list(NAT)), np.isin(C["c30b"], list(NAT))
    lost = na10 & ~nb10 & na30 & ~nb30
    gain = ~na10 & nb10 & ~na30 & nb30
    plant = (C["c10b"] == 9) & (C["c30b"] == 9) & (C["c10a"] != 9) & (C["c30a"] != 9)
    games = sorted(d.glob("game_*.png"))
    ims = [Image.open(p).convert("RGB").resize((T, T)) for p in games]
    ov = ims[1].copy()
    mask = np.zeros((*lost.shape, 4), np.uint8)
    mask[lost] = (255, 40, 40, 170); mask[gain] = (40, 255, 80, 170); mask[plant] = (255, 220, 0, 170)
    ov.paste(Image.fromarray(mask, "RGBA").resize((T, T), Image.NEAREST), (0, 0), Image.fromarray(mask, "RGBA").resize((T, T), Image.NEAREST))
    row = Image.new("RGB", (3 * T + 20, T + 22), (16, 20, 28))
    for i, im in enumerate([ims[0], ims[1], ov]):
        row.paste(im, (i * (T + 10), 22))
    ImageDraw.Draw(row).text((4, 4), f"{cid}  perda(2 mapas)={100*lost.mean():.1f}%  ganho={100*gain.mean():.1f}%  plantio novo={100*plant.mean():.1f}%  "
                             f"[{games[0].stem[5:]} | {games[1].stem[5:]} | sobreposição]", fill=(255, 255, 0))
    rows.append(row)
    print(cid, f"perda {100*lost.mean():.1f}%  ganho {100*gain.mean():.1f}%  plantio {100*plant.mean():.1f}%")
sheet = Image.new("RGB", (rows[0].width, sum(r.height + 6 for r in rows)), (16, 20, 28))
y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.height + 6
out = ROOT / "data" / "qa" / f"evidencia_{a.name}.png"; sheet.save(out); print(out)
