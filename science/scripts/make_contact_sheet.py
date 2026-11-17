"""Folhas de QA visual: cada linha = par (A | B) reduzido + rótulo com Δ MapBiomas e flags.
Uso: python make_contact_sheet.py [--prefix CAP-] [--per-sheet 10] [--name qa]
Saída: data/qa/<name>_NN.png (não versionado; só para inspeção)."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("--ids", nargs="*", default=[]); ap.add_argument("--prefix", default=""); ap.add_argument("--per-sheet", type=int, default=10)
ap.add_argument("--name", default="qa"); ap.add_argument("--thumb", type=int, default=300)
a = ap.parse_args()

dirs = [d for d in sorted((ROOT / "data" / "pairs").iterdir())
        if d.name.startswith(a.prefix) and (not a.ids or d.name in a.ids) and (d / "metadata.json").exists()]
try:
    font = ImageFont.truetype("arial.ttf", 15)
except OSError:
    font = ImageFont.load_default()
T, LBL, PAD = a.thumb, 330, 6
out = ROOT / "data" / "qa"; out.mkdir(parents=True, exist_ok=True)
for s in range(0, len(dirs), a.per_sheet):
    chunk = dirs[s:s + a.per_sheet]
    sheet = Image.new("RGB", (LBL + 2 * T + 3 * PAD, len(chunk) * (T + PAD) + PAD), (18, 24, 32))
    dr = ImageDraw.Draw(sheet)
    for k, d in enumerate(chunk):
        m = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
        y = PAD + k * (T + PAD)
        games = [d / f"game_{im['datetime_utc'][:10]}.png" for im in m["images"]]
        for j, g in enumerate(games[:2]):
            sheet.paste(Image.open(g).convert("RGB").resize((T, T), Image.LANCZOS), (LBL + PAD + j * (T + PAD), y))
        ref = m["reference_mapbiomas"]
        txt = (f"{m['challenge_id']}  [{m['mode']}]\n{m['name'][:40]}\n{m['biome']}\n"
               f"{m['images'][0]['datetime_utc'][:10]} → {m['images'][1]['datetime_utc'][:10]}\n"
               f"Δ10m {ref['delta_pp_10m']:+.1f} pp\nΔ30m {ref['delta_pp_30m']:+.1f} pp\n"
               f"hipótese: {m['selection_hypothesis'][:34]}\nflags: {', '.join(m['qa']['auto_flags']) or '-'}")
        dr.multiline_text((PAD, y + 4), txt, fill=(230, 230, 230), font=font, spacing=5)
    p = out / f"{a.name}_{s // a.per_sheet + 1:02d}.png"
    sheet.save(p, optimize=True); print(p)
