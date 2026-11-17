"""Renderização de prévias e imagens do jogo.

Regra de integridade: os parâmetros de tom (estiramento, gama, saturação) são calculados
UMA vez por par e aplicados IDENTICAMENTE às duas datas. Nunca estirar cada imagem
separadamente: isso faria uma data parecer mais "verde" sem mudança real no terreno.
Ampliação apenas por fator inteiro com Lanczos (interpolação); nenhuma "super-resolução"
que invente detalhes.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TRUE_COLOR = ("red", "green", "blue")
FALSE_COLOR = ("nir", "red", "green")
# estiramento fixo global (triagem/prévias científicas)
STRETCH = {"true": (0.0, 0.18), "false": (0.0, 0.45)}
GAMMA = 1.0 / 1.6


def to_rgb(refl: dict, bands, lim, invalid_mask=None) -> np.ndarray:
    lo, hi = lim
    rgb = np.dstack([refl[b] for b in bands])
    rgb = np.clip((rgb - lo) / (hi - lo), 0, 1) ** GAMMA
    rgb = np.nan_to_num(rgb, nan=0.0)
    img = (rgb * 255).astype("uint8")
    if invalid_mask is not None:  # hachura magenta discreta onde não há dado válido
        img[invalid_mask] = (img[invalid_mask] * 0.35 + np.array([255, 0, 255]) * 0.65).astype("uint8")
    return img


# ---------------- renderização para visão humana (jogo) ----------------

def pair_tone(refl_a: dict, refl_b: dict, valid=None, bands=TRUE_COLOR,
              p_lo=0.5, p_hi=99.0, target_mid=0.36, gamma_range=(0.4, 1.0), saturation=1.12,
              min_range=0.15) -> dict:
    """Parâmetros de tom COMPARTILHADOS pelo par (mesmos números nas duas datas).
    - preto/branco: percentis dos 3 canais juntos (preserva o equilíbrio de cor),
      sobre os pixels válidos das DUAS datas;
    - gama automática: leva a mediana de luminância do par a `target_mid`, para que
      dosséis escuros não virem preto quando há áreas claras (cidade, solo) no recorte."""
    vals, lums = [], []
    for r in (refl_a, refl_b):
        stack = np.dstack([r[b] for b in bands])
        m = np.all(np.isfinite(stack), axis=2)  # nodata isolado não pode virar NaN no tom (bug CAP-SE/MA)
        if valid is not None:
            m &= valid
        vals.append(stack[m].ravel()); lums.append(stack[m].mean(axis=1))
    v = np.concatenate(vals)
    lo, hi = np.percentile(v, [p_lo, p_hi])
    if hi - lo < min_range:  # cena uniforme (floresta contínua): não esticar ruído até virar "neon"
        c = (hi + lo) / 2
        lo, hi = max(c - min_range / 2, float(v.min())), c + min_range / 2
    med = float(np.clip((np.median(np.concatenate(lums)) - lo) / (hi - lo), 1e-3, 0.999))
    gamma = float(np.clip(np.log(target_mid) / np.log(med), *gamma_range))
    return {"bands": list(bands), "black": float(lo), "white": float(hi),
            "gamma": round(gamma, 4), "saturation": float(saturation),
            "percentiles": [p_lo, p_hi], "target_mid": target_mid, "scope": "par (duas datas juntas)"}


def apply_tone(refl: dict, tone: dict) -> np.ndarray:
    rgb = np.dstack([refl[b] for b in tone["bands"]]).astype("float32")
    rgb = np.clip((rgb - tone["black"]) / (tone["white"] - tone["black"]), 0, 1)
    rgb = np.nan_to_num(rgb, nan=0.0) ** tone["gamma"]
    if tone["saturation"] != 1.0:  # saturação em torno da luminância (Rec. 709)
        y = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[..., None]
        rgb = np.clip(y + (rgb - y) * tone["saturation"], 0, 1)
    return (rgb * 255 + 0.5).astype("uint8")


def upscale(img: np.ndarray, factor: int) -> Image.Image:
    im = Image.fromarray(img)
    if factor == 1:
        return im
    return im.resize((im.width * factor, im.height * factor), Image.Resampling.LANCZOS)


def _fonts():
    try:
        return ImageFont.truetype("arial.ttf", 16), ImageFont.truetype("arial.ttf", 13)
    except OSError:
        f = ImageFont.load_default(); return f, f


def side_by_side(img_a, img_b, label_a, label_b, title, out_png, scale_px=None, scale_m=None):
    img_a = np.asarray(img_a); img_b = np.asarray(img_b)
    h, w, _ = img_a.shape
    pad, head = 12, 46
    canvas = Image.new("RGB", (2 * w + 3 * pad, h + head + pad), (18, 24, 32))
    canvas.paste(Image.fromarray(img_a), (pad, head))
    canvas.paste(Image.fromarray(img_b), (2 * pad + w, head))
    d = ImageDraw.Draw(canvas)
    f, fs = _fonts()
    d.text((pad, 4), title, fill=(235, 235, 235), font=f)
    d.text((pad, 25), label_a, fill=(200, 210, 220), font=fs)
    d.text((2 * pad + w, 25), label_b, fill=(200, 210, 220), font=fs)
    if scale_px and scale_m:
        for x0 in (pad, 2 * pad + w):
            y = head + h - 14
            d.rectangle([x0 + 10, y, x0 + 10 + scale_px, y + 4], fill=(255, 255, 255))
            lab = f"{scale_m/1000:g} km" if scale_m >= 1000 else f"{scale_m:g} m"
            d.text((x0 + 10, y - 16), lab, fill=(255, 255, 255), font=fs)
    canvas.save(out_png, optimize=True)
