"""Experiment 17b: tolerance of criterion 3 to deviations between pre-class and recorded enrollment.

Frozen protocol: 研究协议_容忍度.json. Each leave-one-room-out cold_week model is fitted once on the other
rooms' recorded data (exactly as the formal model); only the held-out room's query enrollment is perturbed.
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
PROTOCOL = Path(__file__).with_name('研究协议_容忍度.json')
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R
import unified as U

BIAS = [-.3, -.2, -.1, -.05, 0., .05, .1, .2, .3]
SIGMA = [.05, .1, .2, .3]


def main():
    d = R.load(); folds = {}
    for room in U.ROOMS:
        folds[room] = (U.fit_cold(d[d.room.ne(room)]), d[d.room.eq(room)])
        print('fitted', room, flush=True)

    def macro(perturb):
        out = []
        for room, (bundle, query) in folds.items():
            q = query.copy(); q['enrollments'] = perturb(q.enrollments.to_numpy(float))
            out.append(R.metrics(query.occupancy_rate, U.predict_cold(bundle, q))['rmse'])
        return float(np.mean(out)), dict(zip(folds, map(float, out)))

    report = dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), bias={}, noise={})
    for b in BIAS:
        m, rooms = macro(lambda e, b=b: e * (1 + b)); report['bias'][f'{b:+.2f}'] = dict(macro_rmse=m, pass_018=m <= .18, rooms=rooms)
        print('bias', b, round(m, 4), flush=True)
    for s in SIGMA:
        vals = [macro(lambda e, s=s, k=k: e * np.exp(np.random.default_rng(k).normal(0, s, len(e))))[0] for k in range(5)]
        report['noise'][f'{s:.2f}'] = dict(macro_rmse_mean=float(np.mean(vals)), macro_rmse_seeds=vals, pass_018=float(np.mean(vals)) <= .18)
        print('noise', s, round(float(np.mean(vals)), 4), flush=True)
    ok_b = [abs(float(k)) for k, v in report['bias'].items() if v['pass_018']]
    report['tolerance'] = dict(
        max_abs_bias_all_pass=max(x for x in [0, .05, .1, .2, .3] if all(report['bias'][f'{s:+.2f}']['pass_018'] for s in (x, -x))),
        max_sigma_pass=max([0.] + [float(k) for k, v in report['noise'].items() if v['pass_018']]),
        downward_bias_pass=[k for k, v in report['bias'].items() if v['pass_018'] and float(k) < 0],
        upward_bias_pass=[k for k, v in report['bias'].items() if v['pass_018'] and float(k) > 0])
    (OUT / 'tolerance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print('SUMMARY', json.dumps(report['tolerance'], ensure_ascii=False))


if __name__ == '__main__':
    main()
