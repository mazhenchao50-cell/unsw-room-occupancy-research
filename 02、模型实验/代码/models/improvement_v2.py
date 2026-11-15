# -*- coding: utf-8 -*-
"""Improvement v2 (2026-10-29): same-size room prior for LORO cold start.

Hypothesis: in LORO the held-out room has no own course history, so the model
falls back to a GLOBAL mean across all other rooms. Small rooms (35 seats) and
large rooms (497 seats) have very different occupancy levels. We replace the
global fallback with a same-size-band mean (rooms in the same seats bin,
EXCLUDING the held-out room itself to avoid leakage).

Implementation: monkey-patch revised.history with a v2 version that knows the
held-out room and seats bin. Everything else (features, tuning, folds) stays
identical to revised.py, so the only change is the prior.
"""
from pathlib import Path
import sys, json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "02、模型实验" / "代码" / "models"))
import revised as R

OUT = ROOT / "02、模型实验" / "生成产物" / "improvement_v2"
OUT.mkdir(parents=True, exist_ok=True)

_orig = sys.stdout
log = open(OUT / "improvement_v2.log", "w", encoding="utf-8")
class Tee:
    def write(self, s): _orig.write(s); log.write(s)
    def flush(self): _orig.flush(); log.flush()
sys.stdout = Tee()

d = R.load()

# seats bins
seats = d.groupby("room").seats.first().to_dict()
def band(s):
    if s <= 80: return "small"
    if s <= 300: return "medium"
    return "large"
BAND = {r: band(s) for r, s in seats.items()}
print("seats bins:")
for r, b in sorted(BAND.items(), key=lambda x: seats[x[0]]):
    print(f"  {r:12s} seats={seats[r]:6.0f}  band={b}")

def make_history_v2(held_room):
    same_bin = [r for r in BAND if BAND[r] == BAND[held_room]]
    def history_v2(reference, query):
        out = []
        for row in query.itertuples():
            past = reference[reference.date < row.date]
            course = past.loc[past.course_id.eq(row.course_id), "occupancy_rate"]
            bin_past = past[past.room.isin(same_bin)]
            bin_prior = float(bin_past.occupancy_rate.mean()) if len(bin_past) else None
            global_prior = float(past.occupancy_rate.mean()) if len(past) else 0.3
            prior = bin_prior if bin_prior is not None else global_prior
            out.append((float(course.mean()) if len(course) else prior, len(course)))
        return pd.DataFrame(out, columns=["course_hist_mean", "course_hist_n"], index=query.index)
    history_v2.__held_room__ = held_room
    history_v2.__same_bin__ = same_bin
    return history_v2

rooms = sorted(d.room.unique())
results = {}
for room in rooms:
    te = d[d.room == room]
    available = d[d.room != room]
    tr = available[available.week < 11]
    va = available[available.week == 11]
    # patch history
    R.history = make_history_v2(room)
    p, bundle, _ = R.fit_selected("LightGBM", tr, va, available, te)
    met = R.metrics(te.occupancy_rate, p)
    results[room] = {"rmse": round(met["rmse"], 4), "mae": round(met["mae"], 4),
                     "n": len(te), "band": BAND[room], "same_bin_rooms": R.history.__same_bin__}
    print(f"[LORO v2] held={room:12s} band={BAND[room]:6s} rmse={met['rmse']:.4f} mae={met['mae']:.4f}")

# restore original
R.history = __import__("revised").history.__wrapped__ if hasattr(R.history, "__wrapped__") else None
macro = float(np.mean([v["rmse"] for v in results.values()]))
print(f"\n[LORO v2] macro RMSE = {macro:.4f}")
print(f"[LORO v1 baseline] macro RMSE = 0.2279 (from improvement_v1 / report.json)")
print(f"[LORO v2 improvement] = {(0.2279 - macro)/0.2279*100:+.2f}%")

# random comparator for gap (same as revised.py)
R.history = R.load.__globals__["history"] if "history" in R.load.__globals__ else None
# safer: just re-import a fresh module reference
import importlib; importlib.reload(R)
ix = np.arange(len(d))
from sklearn.model_selection import train_test_split
it, ie = train_test_split(ix, test_size=0.2, random_state=R.SEED)
itr, iv = train_test_split(it, test_size=0.2, random_state=R.SEED)
p_rand, _, _ = R.fit_selected("LightGBM", d.iloc[itr], d.iloc[iv], d.iloc[it], d.iloc[ie])
rand_rmse = float(np.sqrt(np.mean((p_rand - d.iloc[ie].occupancy_rate.to_numpy())**2)))
gap = (macro - rand_rmse) / rand_rmse
print(f"\nRandom split RMSE = {rand_rmse:.4f}")
print(f"LORO v2 gap vs random = {gap*100:.2f}%  (acceptance: gap<=30% or macro<=0.18 -> "
      f"{'PASS' if (macro<=0.18 or gap<=0.30) else 'FAIL'})")

report = {
    "experiment": "improvement_v2",
    "date": "2026-10-29",
    "hypothesis": "Replace global-mean cold-start prior with same-seats-band mean (excluding held room).",
    "seats_bins": BAND,
    "per_room": results,
    "macro_rmse": round(macro, 4),
    "v1_macro_rmse": 0.2279,
    "relative_change_pct": round((0.2279 - macro) / 0.2279 * 100, 2),
    "random_split_rmse": round(rand_rmse, 4),
    "gap_vs_random_pct": round(gap * 100, 2),
    "acceptance": "macro<=0.18 or gap<=0.30",
}
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved: {OUT/'report.json'}")
log.close()
