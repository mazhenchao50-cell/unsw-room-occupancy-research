# -*- coding: utf-8 -*-
"""
Phase 1 数据管道：清洗 -> week9/10去重 -> Session聚合 -> 双口径标签
基于 heals(heal_base.py) 复用，新增：
  1) 10/2(周一) 在 week9 与 week10 重叠的去重（保留 week10 完整数据，week9 该日删除）
  2) Session 聚合：教室+日期+课程(非NA)，每 Session 取 max(NumAttendees)
  3) 双口径标签：occupancy_rate = NumAttendees/NumSeats ; attend_rate = attendance/enrollment
  4) 质量报告 + 结果落盘
"""
from __future__ import annotations

import json
import os
import sys
import argparse
import hashlib
from pathlib import Path
import numpy as np
from datetime import date

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
parser = argparse.ArgumentParser()
parser.add_argument('--data-dir', type=Path, default=Path(ROOT) / '01、数据处理' / '原始数据' / 'UNSW')
parser.add_argument('--out-dir', type=Path, default=Path(ROOT) / '01、数据处理' / '清洗产物')
args = parser.parse_args()
DATA_DIR = str(args.data_dir.resolve())
OUT_DIR = str(args.out_dir.resolve())
os.makedirs(OUT_DIR, exist_ok=True)

import heal_base  # 复用清洗层

# ---------------------------------------------------------------------------
# 1. 加载与清洗（复用 heal_base；add_src 保留文件来源用于去重）
# ---------------------------------------------------------------------------
ledger = heal_base.QualityLedger()
att = heal_base.load_attendance(DATA_DIR, ledger)          # 出席数据（2017+2018，清洗后）
comp = heal_base.load_computed(DATA_DIR, ledger, add_src=True)  # 传感器事件（清洗后，含 src_week）
rep = {"attendance_rows": int(len(att)), "computed_rows": int(len(comp))}
print(f"[load] attendance rows={len(att)}, computed rows={len(comp)}")

# ---------------------------------------------------------------------------
# 2. 文件级去重：10/2 的行同时存在于 week9 与 week10 两个文件（其 Week 字段=10）
#    按 src_week 删除 week9 文件中的 10/2 重复行（保留 week10 文件中的完整周一）
# ---------------------------------------------------------------------------
dup_date = date(2017, 10, 2)
mask_dup = (comp["src_week"] == 9) & (comp["date"] == dup_date)
n_dup = int(mask_dup.sum())
compare_cols = [c for c in comp.columns if c != 'src_week']
right = comp.loc[(comp['src_week'] == 10) & (comp['date'] == dup_date), compare_cols].drop_duplicates()
matched = comp.loc[mask_dup, compare_cols].merge(right, on=compare_cols, how='left', indicator=True, validate='many_to_one')
exact_duplicates = int((matched['_merge'] == 'both').sum())
comp = comp[~mask_dup].copy()
print(f"[dedup] removed week9-file 10/2 rows = {n_dup}")
assert int(((comp["week"] == 10) & (comp["date"] == dup_date)).sum()) > 0

# week9 文件现状：仅剩 9/28、9/29 两天（异常周，训练切分时整周排除）
w9_days = sorted({d for d in comp.loc[comp["week"] == 9, "date"]})
print(f"[week9] remaining days = {w9_days}")

# ---------------------------------------------------------------------------
# 3. Session 聚合：教室 + 日期 + 课程(非NA)，向量化
# ---------------------------------------------------------------------------
c = comp[comp["course_id"].notna()].copy()
time_counts = c.groupby(['room_code', 'date', 'course_id'])[['course_start', 'course_end']].nunique(dropna=False)
if (time_counts > 1).any().any():
    raise ValueError('A session key has multiple start/end times; revise aggregation instead of silently merging classes.')
g = c.groupby(["room_code", "date", "course_id"], as_index=False).agg({
    "week": "first",
    "course_start": "first",
    "course_end": "first",
    "doors": "max",
    "seats": "max",
    "num_enrollments": "max",
    "num_attendees": "max",
}).rename(columns={
    "room_code": "room",
    "num_enrollments": "enrollments",
    "num_attendees": "attendees",
})
g["date"] = pd.to_datetime(g["date"])
g["weekday"] = g["date"].dt.weekday           # 周一=0
g["is_weekend"] = g["weekday"].apply(lambda x: 1 if x >= 5 else 0)
g["is_morning"] = g["course_start"].apply(
    lambda x: 1 if x is not None and int(str(x)[:2]) < 12 else 0)
g["occupancy_rate"] = (g["attendees"] / g["seats"]).round(4)
g["attend_rate"] = (g["attendees"] / g["enrollments"].where(g["enrollments"] > 0)).round(4)

# 与 2017 出席数据对齐（enrollment 权威来源）
att17 = att[(att["year"] == 2017)].copy()
att17["date"] = pd.to_datetime(att17["date"])
keys = ['date', 'room', 'course_start', 'course_end']
schedule = att17.rename(columns={'room_code': 'room', 'start_time': 'course_start', 'end_time': 'course_end', 'enrollment': 'enroll_sched', 'attendance': 'attend_sched'})
# Multiple timetable records may share a slot. Do not guess an authoritative value.
ambiguous = schedule.duplicated(keys, keep=False)
ambiguous_keys = schedule.loc[ambiguous, keys].drop_duplicates()
unique_schedule = schedule.loc[~ambiguous, keys + ['enroll_sched', 'attend_sched']]
n_before = len(g)
g = g.merge(unique_schedule, on=keys, how='left', validate='many_to_one', indicator=True)
g['schedule_match'] = g.pop('_merge').astype(str).replace({'both': 'matched', 'left_only': 'unmatched'})
g = g.merge(ambiguous_keys.assign(ambiguous_slot=True), on=keys, how='left', validate='many_to_one')
g.loc[g.pop('ambiguous_slot').eq(True), 'schedule_match'] = 'ambiguous'
assert len(g) == n_before
assert not np.isinf(g.select_dtypes(include='number').to_numpy(dtype=float, na_value=np.nan)).any()
g['session_id'] = g['date'].dt.strftime('%Y-%m-%d') + '|' + g['room'] + '|' + g['course_id']
assert g.session_id.is_unique

g = g.sort_values(["date", "room", "course_id"]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# 4. 落盘 + 质量报告
# ---------------------------------------------------------------------------
comp.to_csv(os.path.join(OUT_DIR, "clean_computed.csv"), index=False, encoding="utf-8-sig")
g.to_csv(os.path.join(OUT_DIR, "sessions.csv"), index=False, encoding="utf-8-sig")
att.to_csv(os.path.join(OUT_DIR, "attendance_clean.csv"), index=False, encoding="utf-8-sig")

report = {
    "phase": 1,
    "input": {
        "attendance_rows": int(len(att)),
        "computed_rows_after_dedup": int(len(comp)),
        "computed_rows_before_dedup": rep["computed_rows"],
    },
    "dedup": {
        "week9_102_removed": n_dup,
        "exact_duplicate_rows": exact_duplicates,
        "source_policy_discarded_rows": n_dup - exact_duplicates,
        "week9_remaining_days": [str(d) for d in w9_days],
    },
    "sessions": {
        "total": len(g),
        "valid_labels": int(g.occupancy_rate.notna().sum()),
        "experiment_rows_excluding_week9": int((g.occupancy_rate.notna() & g.week.ne(9)).sum()),
        "rate_denominator": "all sessions; missing labels are separately counted",
        "schedule_match": g.schedule_match.value_counts().to_dict(),
        "no_show": int((g["attendees"] == 0).sum()),
        "no_show_rate": round(float((g["attendees"] == 0).mean()), 4),
        "low_util_lt10pct_incl0": int((g["occupancy_rate"] < 0.10).sum()),
        "low_util_rate": round(float((g["occupancy_rate"] < 0.10).mean()), 4),
        "over_capacity": int((g["attendees"] > g["seats"]).sum()),
        "rooms": sorted(g["room"].unique().tolist()),
        "weeks": sorted(int(w) for w in g["week"].unique()),
        "course_ids": int(g["course_id"].nunique()),
        "date_range": [str(g["date"].min().date()), str(g["date"].max().date())],
    },
}
with open(os.path.join(OUT_DIR, "pipeline_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)

quality = {'normalization_ledger': ledger.to_list(), 'note': 'Format normalization is not missing-value completion or a quality score.',
           'missing_by_column': g.isna().sum().astype(int).to_dict(), 'infinite_values': 0,
           'invalid_enrollment_denominator': int((g.enrollments.isna() | g.enrollments.le(0)).sum()),
           'schedule_match': g.schedule_match.value_counts().to_dict()}
Path(OUT_DIR, 'quality_report.json').write_text(json.dumps(quality, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
manifest = {'download_date': None, 'publisher_checksum': None, 'license_verification': 'pending original release evidence',
            'note': 'Local SHA256 establishes this revision input, not original download authenticity.',
            'files': [{'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in sorted(Path(DATA_DIR).glob('*.csv'))]}
Path(OUT_DIR, 'input_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

print(json.dumps(report, ensure_ascii=False, indent=2))
print("DONE ->", OUT_DIR)
