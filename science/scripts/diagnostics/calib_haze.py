"""Calibra um indicador de fumaça/névoa com cenas já classificadas visualmente.
Indicadores: AOT médio (L2A, escala 0.001) e reflectância azul (B02) mediana."""
import sys
from pathlib import Path

import numpy as np
from pystac_client import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from geodet import s2  # noqa: E402

CASES = [  # (rótulo visual, item, lon, lat)
    ("FUMACA", "S2A_T21KWA_20200928T140058_L2A", -56.85, -17.35),
    ("FUMACA", "S2A_T21KWA_20201008T140058_L2A", -56.85, -17.35),
    ("FUMACA", "S2B_T20MPS_20240802T142713_L2A", -61.65, -7.95),
    ("LIMPA", "S2C_T21KWA_20251002T135934_L2A", -56.85, -17.35),
    ("LIMPA", "S2B_T20MPS_20200803T142734_L2A", -61.65, -7.95),
    ("LIMPA", "S2B_T20LLQ_20200727T143729_L2A", -64.47, -9.79),
    ("LIMPA", "S2B_T20LLQ_20240726T144346_L2A", -64.47, -9.79),
    ("LIMPA", "S2B_T22KCC_20240529T134749_L2A", -51.97, -20.55),
    ("NUVEM_FINA", "S2B_T20MRB_20200721T141737_L2A", -59.95, -2.95),
    ("LIMPA", "S2B_T20MRB_20240720T141713_L2A", -59.95, -2.95),
]
col = Client.open(s2.EARTH_SEARCH).get_collection(s2.COLLECTION)
for lab, iid, lon, lat in CASES:
    it = col.get_item(iid)
    g = s2.make_grid(lon, lat, 12000, 60.0)
    aot = s2._read(it.assets["aot"].href, g, dtype="float32") * 0.001
    blue = s2._read(it.assets["blue"].href, g, dtype="float32") * 1e-4 - 0.1
    red = s2._read(it.assets["red"].href, g, dtype="float32") * 1e-4 - 0.1
    haze = ((blue > 0.06) & (blue >= 0.95 * red)).mean()
    print(f"{lab:10} {iid[:28]}  AOT med={np.median(aot):.3f}  "
          f"B02 p10={np.percentile(blue,10):.3f}  haze_frac={haze:.3f}")
