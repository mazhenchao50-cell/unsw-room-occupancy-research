"""L023: fixed two-week history adaptation with a forward-time holdout."""
from pathlib import Path
import hashlib
import importlib.metadata
import platform
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revised as R
from improvement_v3 import capacity_history, using_history

PROTOCOL = {
    'adaptation_weeks': [1, 2], 'source_train_weeks': list(range(1, 9)),
    'source_validation_weeks': [10], 'test_weeks': [11, 12],
    'model': 'LightGBM', 'tree_grid': [80, 200, 400],
    'history': 'v3 capacity-weighted fallback; course mean when available',
    'adaptation': 'Frozen source model and imputation; only prediction history reference is augmented.',
    'scope': 'Retrospective joint room/time holdout; no new blind test, no original LORO KPI verdict.',
}


def split_fold(d, room):
    source = d[d.room.ne(room)]
    train = source[source.week.isin(PROTOCOL['source_train_weeks'])]
    valid = source[source.week.isin(PROTOCOL['source_validation_weeks'])]
    final = pd.concat([train, valid]).sort_values('date')
    adaptation = d[d.room.eq(room) & d.week.isin(PROTOCOL['adaptation_weeks'])]
    test = d[d.room.eq(room) & d.week.isin(PROTOCOL['test_weeks'])]
    if any(x.empty for x in [train, valid, adaptation, test]):
        raise ValueError(f'Incomplete fold: {room}')
    assert train.date.max() < valid.date.min()
    assert max(final.date.max(), adaptation.date.max()) < test.date.min()
    assert set(final.session_id).isdisjoint(test.session_id)
    assert set(adaptation.session_id).isdisjoint(test.session_id)
    return train, valid, final, adaptation, test


def fold_predictions(train, valid, final, adaptation, test):
    with using_history(capacity_history):
        cold, bundle, trials = R.fit_selected('LightGBM', train, valid, final, test)
        augmented = pd.concat([final, adaptation]).sort_values('date')
        warm = R.predict(dict(bundle, reference=augmented), test)
        means = capacity_history(augmented, test)
    preds = {
        'cold_source_model': cold,
        'two_week_history_model': warm,
        'two_week_course_mean': means.course_hist_mean.to_numpy(),
        'two_week_room_mean': np.full(len(test), float(adaptation.occupancy_rate.mean())),
    }
    own_known = test.course_id.isin(adaptation.course_id)
    evidence = {
        'selected_trees': bundle['setting'], 'selection_trials': trials,
        'source_training_n': len(train), 'source_validation_n': len(valid),
        'source_final_n': len(final), 'adaptation_n': len(adaptation), 'test_n': len(test),
        'source_final_max_date': str(final.date.max().date()),
        'adaptation_max_date': str(adaptation.date.max().date()),
        'test_min_date': str(test.date.min().date()),
        'own_course_history_test_n': int(own_known.sum()),
        'adaptation_session_ids': adaptation.session_id.tolist(),
        'source_session_ids': final.session_id.tolist(),
        'test_session_ids': test.session_id.tolist(),
    }
    return preds, evidence, own_known


def run():
    out = R.ROOT / '02、模型实验/生成产物/improvement_v4'
    out.mkdir(parents=True, exist_ok=True)
    # Save the fixed choices before any evaluation. No test-driven search.
    R.dump(out / 'protocol.json', PROTOCOL)
    d = R.load()
    frames, folds = [], {}
    with (out / 'run.log').open('w', encoding='utf-8') as log:
        for room in sorted(d.room.unique()):
            preds, evidence, own_known = fold_predictions(*split_fold(d, room))
            test = split_fold(d, room)[-1]
            folds[room] = evidence
            for name, p in preds.items():
                frames.append(R.prediction_frame(test, p, method=name, own_course_history=own_known.to_numpy()))
            line = f'{room}: ' + ', '.join(f'{k}={R.metrics(test.occupancy_rate,p)["rmse"]:.4f}' for k,p in preds.items())
            print(line, flush=True)
            log.write(line + '\n')
            log.flush()
    all_predictions = pd.concat(frames, ignore_index=True)
    all_predictions.to_csv(out / 'predictions.csv', index=False)
    methods = {}
    expected = set(d[d.week.isin(PROTOCOL['test_weeks'])].session_id)
    for name, frame in all_predictions.groupby('method'):
        assert frame.session_id.is_unique and set(frame.session_id) == expected
        per_room = {room: R.metrics(f.occupancy_rate, f.prediction) for room, f in frame.groupby('room')}
        methods[name] = {
            'micro': R.metrics(frame.occupancy_rate, frame.prediction),
            'macro_rmse': float(np.mean([v['rmse'] for v in per_room.values()])),
            'per_room': per_room,
            'per_week': {str(w): R.metrics(f.occupancy_rate, f.prediction) for w,f in frame.groupby('week')},
            'by_own_course_history': {str(bool(k)): R.metrics(f.occupancy_rate, f.prediction)
                                      for k,f in frame.groupby('own_course_history')},
        }
    cold = methods['cold_source_model']['macro_rmse']
    warm = methods['two_week_history_model']['macro_rmse']
    report = {
        'experiment': 'improvement_v4', 'date': '2026-10-31', 'protocol': PROTOCOL,
        'methods': methods, 'folds': folds,
        'history_model_relative_macro_improvement': 1 - warm / cold,
        'original_cold_start_acceptance': 'Not evaluated here; previous L022 remains unmet.',
        'environment': {'python': platform.python_version(), 'versions': {
            k: importlib.metadata.version(k) for k in ['numpy', 'pandas', 'scikit-learn', 'lightgbm']}},
        'sha256': {str(p.relative_to(R.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [Path(__file__), Path(R.__file__), Path(__file__).with_name('improvement_v3.py'),
                             R.ROOT / '01、数据处理/清洗产物/sessions.csv', out / 'protocol.json']},
    }
    R.dump(out / 'report.json', report)
    print({k: v['macro_rmse'] for k,v in methods.items()}, flush=True)
    return report


if __name__ == '__main__':
    run()
