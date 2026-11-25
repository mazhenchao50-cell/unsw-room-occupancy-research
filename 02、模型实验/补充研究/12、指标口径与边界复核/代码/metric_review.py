"""Experiment 12: how robust are the business-plan gates ①②③ to reasonable readings of their wording?

Not a model change. Uses the formal unified_v5 saved predictions and refits only what a reading
requires (baselines per fold; the same cold model on the fixed random split). Plan wording
(3조 사업계획서, 평가방법):
 ① 점유율(0~1) 예측 오차 RMSE·MAE, Baseline(시간표 static, 역사 평균) 대비 RMSE 10% 이상 개선
 ② 점유율 10% 미만을 빈 강의실로 분류, F1 ≥ 0.60 (또는 Precision ≥ 0.65)
 ③ LORO 평균 RMSE, Random split 대비 성능 격차 30% 이내 (또는 평균 RMSE ≤ 0.18)
Plan preprocessing also states occupancy outliers are clipped to [0,1].
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R
import cold_week as COLD

U = ROOT / '02、模型实验/生成产物/unified'


def rmse(y, p): return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))
def clip(v): return np.clip(np.asarray(v, float), 0, 1)


def gate1():
    d = R.load(); weeks = sorted(d.week.unique()); f = pd.read_csv(U / 'time_predictions.csv'); out = {}
    for tw in (8, 10, 11, 12):
        i = weeks.index(tw); vw = weeks[i - 2]; final = d[d.week <= vw]; test = d[d.week.eq(tw)]
        b = R.baselines(final, test); g = f[f.week.eq(tw)].set_index('session_id').loc[test.session_id]
        y, p = test.occupancy_rate.to_numpy(), g.prediction.to_numpy()
        s = (test.enrollments.fillna(final.enrollments.median()) / test.seats).to_numpy()
        fs = (final.enrollments.fillna(final.enrollments.median()) / final.seats).to_numpy()
        k = float(np.sum(final.occupancy_rate * fs) / np.sum(fs ** 2))  # training-only attendance ratio
        bases = dict(timetable_static=b['timetable_static'], historical_mean=b['historical_mean'],
                     course_history_mean=b['course_history_mean'], timetable_scaled=np.maximum(0, k * s))
        row = dict(model_rmse=rmse(y, p), model_rmse_clipped=rmse(clip(y), clip(p)), timetable_scale_k=k)
        for name, v in bases.items():
            row[name] = dict(rmse=rmse(y, v), gain=1 - rmse(y, p) / rmse(y, v),
                             gain_clipped=1 - rmse(clip(y), clip(p)) / rmse(clip(y), clip(v)))
        out[str(tw)] = row
    return out


def gate2():
    f = pd.read_csv(U / 'time_predictions.csv'); y = f.occupancy_rate.lt(.1)
    rules = dict(official_union=f.low_alert, without_calendar=f.model_alert | f.context_alert,
                 classifier_only=f.model_alert, context_only=f.context_alert, regression_below_010=(f.regression_prediction if 'regression_prediction' in f else f.prediction).lt(.1))
    if 'state_prediction' in f: rules['state_below_010'] = f.state_prediction.lt(.1)
    out = {}
    for name, a in rules.items():
        per = {str(w): R.binary_metrics(y[f.week.eq(w)], a[f.week.eq(w)]) for w in (8, 10, 11, 12)}
        pooled = R.binary_metrics(y, a)
        out[name] = dict(weekly={w: dict(precision=m['precision'], recall=m['recall'], f1=m['f1'],
                                         passes=bool(m['f1'] >= .6 or m['precision'] >= .65)) for w, m in per.items()},
                         pooled=dict(precision=pooled['precision'], recall=pooled['recall'], f1=pooled['f1']),
                         all_weeks_pass=all(m['f1'] >= .6 or m['precision'] >= .65 for m in per.values()),
                         precision_branch_only_weeks=[w for w, m in per.items() if m['f1'] < .6 and m['precision'] >= .65])
    return out


def gate3():
    d = R.load(); s = pd.read_csv(U / 'spatial_predictions.csv'); rnd = pd.read_csv(U / 'random_predictions.csv')
    macro = float(np.mean([rmse(g.occupancy_rate, g.prediction) for _, g in s.groupby('room')]))
    macro_c = float(np.mean([rmse(clip(g.occupancy_rate), clip(g.prediction)) for _, g in s.groupby('room')]))
    micro, micro_c = rmse(s.occupancy_rate, s.prediction), rmse(clip(s.occupancy_rate), clip(s.prediction))
    r_known, r_known_c = rmse(rnd.occupancy_rate, rnd.prediction), rmse(clip(rnd.occupancy_rate), clip(rnd.prediction))
    it, ie = train_test_split(np.arange(len(d)), test_size=.2, random_state=42)
    cold = COLD.fit(d.iloc[it]); pc = COLD.predict(cold, d.iloc[ie]); yc = d.iloc[ie].occupancy_rate.to_numpy()
    r_same, r_same_c = rmse(yc, pc), rmse(clip(yc), clip(pc))
    pd.DataFrame(dict(session_id=d.iloc[ie].session_id.to_numpy(), occupancy_rate=yc, prediction=pc)).to_csv(OUT / '同模型随机对照预测.csv', index=False)
    variants = {}
    for label, m, rk, rs in [('macro', macro, r_known, r_same), ('macro_clipped', macro_c, r_known_c, r_same_c),
                             ('micro', micro, r_known, r_same), ('micro_clipped', micro_c, r_known_c, r_same_c)]:
        variants[label] = dict(loro_rmse=m, abs_018=bool(m <= .18),
                               gap_vs_router_random=m / rk - 1, gap_router_le_030=bool(m / rk - 1 <= .3),
                               gap_vs_same_model_random=m / rs - 1, gap_same_le_030=bool(m / rs - 1 <= .3))
    return dict(router_random_rmse=r_known, same_model_random_rmse=r_same, same_model_selected=cold['selected'],
                variants=variants, rooms_over_018=int(sum(rmse(g.occupancy_rate, g.prediction) > .18 for _, g in s.groupby('room'))))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(model=json.loads((U / 'report.json').read_text(encoding='utf-8'))['protocol']['version'],
                  gate1=gate1(), gate2=gate2(), gate3=gate3(), formal_changed=False,
                  sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                          ['02、模型实验/生成产物/unified/time_predictions.csv', '02、模型实验/生成产物/unified/spatial_predictions.csv',
                           '02、模型实验/生成产物/unified/random_predictions.csv', '01、数据处理/清洗产物/sessions.csv']})
    report['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    R.dump(OUT / 'report.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=1)[:6000])


if __name__ == '__main__':
    main()
