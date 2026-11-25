"""Experiment 18: SHAP explanation of the frozen unified_v6 week-12 fold (conditional regression m1 and classifier trees).

Frozen protocol: 研究协议.json. Loads fold_models/rolling_12.joblib; never refits or changes predictions.
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd
import joblib
import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / '生成产物'
PROTOCOL = Path(__file__).with_name('研究协议.json')
sys.path.insert(0, str(ROOT / '02、模型实验/代码/models'))
import revised as R
import stable_low as LOW


def explain(model, x, name):
    sv = shap.TreeExplainer(model).shap_values(x)
    if isinstance(sv, list): sv = sv[1]                      # binary classifier: positive (low-use) class
    sv = np.asarray(sv)
    if sv.ndim == 3: sv = sv[:, :, 1]
    imp = pd.DataFrame(dict(feature=x.columns, mean_abs_shap=np.abs(sv).mean(0),
        direction=[float(spearmanr(x[c], sv[:, i]).correlation) if x[c].nunique() > 1 else 0.0 for i, c in enumerate(x.columns)]))
    imp = imp.sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)
    imp.to_csv(OUT / f'{name}_重要度.csv', index=False, encoding='utf-8-sig')
    for kind in ('bar', 'dot'):
        plt.figure(); shap.summary_plot(sv, x, plot_type=kind, show=False, max_display=12)
        plt.tight_layout(); plt.savefig(OUT / f'{name}_{"bar" if kind == "bar" else "beeswarm"}.png', dpi=160); plt.close('all')
    return imp, sv


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    bundle = joblib.load(ROOT / '02、模型实验/生成产物/unified/fold_models/rolling_12.joblib')
    d = R.load(); test = d[d.week.eq(12)]
    cond = bundle['cond']
    xm = R.raw_features(cond['reference'], test, cond['use_history']).fillna(cond['median'])[cond['features']]
    np.testing.assert_allclose(np.maximum(0, cond['model'].predict(xm)), R.predict(cond, test))   # same inputs as serving
    low = bundle['low']
    xc = LOW.features(low['reference'], test).fillna(low['median'])[low['features']]
    m_imp, _ = explain(cond['model'], xm, 'm1条件回归')
    c_imp, _ = explain(low['trees'], xc, '低利用分类器')
    checks = {}
    for part, imp in (('m1', m_imp), ('classifier_low_probability', c_imp)):
        for feat, text in protocol['expected_directions'][part].items():
            row = imp[imp.feature.eq(feat)]
            sign = '+' if text.startswith('+') else '−'
            obs = float(row.direction.iloc[0]) if len(row) else None
            checks[f'{part}:{feat}'] = dict(expected=sign, spearman=obs, rank=int(row.index[0]) + 1 if len(row) else None,
                consistent=bool(obs is not None and ((obs > 0) if sign == '+' else (obs < 0))))
    report = dict(protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), n=int(len(test)),
        m1_top=m_imp.head(10).to_dict('records'), classifier_top=c_imp.head(10).to_dict('records'), direction_checks=checks)
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print(json.dumps(dict(m1=m_imp.head(6)[['feature', 'mean_abs_shap', 'direction']].round(4).to_dict('records'),
        clf=c_imp.head(6)[['feature', 'mean_abs_shap', 'direction']].round(4).to_dict('records'), checks=checks), ensure_ascii=False))


if __name__ == '__main__':
    main()
