"""Where do the ② positives come from? Compare sensor-session low-use labels with the authors' attendance table.

The 2019 paper (PDF p.8) removed classes with no attendance or cancelled classes before publishing its
attendance table. Sessions without a unique attendance-table match are therefore candidates for
"scheduled but not held". The match flag is post-hoc and is never used as a model feature.
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = R.load(); m['matched'] = m.schedule_match.eq('matched') & m.attend_sched.notna(); m['low'] = m.occupancy_rate.lt(.1)
    mm = m[m.matched]; occ_att = mm.attend_sched / mm.seats
    a = pd.read_csv(ROOT / '01、数据处理/清洗产物/attendance_clean.csv'); a['occ'] = a.attendance / a.seats
    f = pd.read_csv(ROOT / '02、模型实验/生成产物/unified/time_predictions.csv').merge(m[['session_id', 'matched']], on='session_id', validate='one_to_one')
    by_match = {('matched' if k else 'unmatched'): dict(sessions=len(g), **{x: R.binary_metrics(g.occupancy_rate.lt(.1), g.low_alert)[x]
                for x in ('actual_positive', 'predicted_positive', 'precision', 'recall', 'f1', 'confusion_tn_fp_fn_tp')}) for k, g in f.groupby('matched')}
    report = dict(
        cohort=len(m), match_counts=m.schedule_match.value_counts().to_dict(),
        low_total=int(m.low.sum()), low_in_matched=int(mm.low.sum()), low_in_unmatched=int(m.loc[~m.matched, 'low'].sum()),
        unmatched_low_rate=float(m.loc[~m.matched, 'low'].mean()), matched_low_rate=float(mm.low.mean()),
        zero_peak_unmatched=int((m.loc[~m.matched, 'attendees'] == 0).sum()), zero_peak_total=int((m.attendees == 0).sum()),
        matched_peak_vs_attendance=dict(correlation=float(np.corrcoef(mm.attendees, mm.attend_sched)[0, 1]),
                                        median_ratio=float((mm.attend_sched / mm.attendees.replace(0, np.nan)).median()),
                                        both_low=int((mm.low & occ_att.lt(.1)).sum()), sensor_low_only=int((mm.low & ~occ_att.lt(.1)).sum()),
                                        attendance_low_only=int((~mm.low & occ_att.lt(.1)).sum())),
        attendance_table_low_by_year={str(y): dict(rows=len(g), low=int(g.occ.lt(.1).sum()), zero=int(g.attendance.eq(0).sum())) for y, g in a.groupby('year')},
        unmatched_low_by_week={str(int(w)): [int(g.low.sum()), len(g)] for w, g in m[~m.matched].groupby('week')},
        formal_alerts_by_match=by_match,
        interpretation='四个评估周222条正例中221条为考勤表无唯一匹配课次；原论文清洗时删除无出席或取消课次。②主要识别“课表有但未实际上课”的课次（与计划书No-show定义一致）。匹配标记为事后信息，不作为特征。2018考勤表没有低利用率课次，②无法在2018年验证。',
        sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ['01、数据处理/清洗产物/sessions.csv', '01、数据处理/清洗产物/attendance_clean.csv', '02、模型实验/生成产物/unified/time_predictions.csv']})
    R.dump(OUT / '标签来源分析.json', report)
    print(json.dumps({k: report[k] for k in ('low_total', 'low_in_matched', 'low_in_unmatched', 'formal_alerts_by_match')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
