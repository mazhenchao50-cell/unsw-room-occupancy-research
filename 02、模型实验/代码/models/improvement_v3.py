"""Retrospective L022: query-specific continuous capacity prior, fixed bandwidth."""
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revised as R


def capacity_history(reference, query):
    """Past-only session weights; capacity ratio 2 has weight 0.5.

    Bandwidth log(2) is fixed before this experiment, not selected on held rooms.
    Known-course history preserves the original implementation.
    """
    out = []
    for row in query.itertuples():
        past = reference[reference.date < row.date]
        course = past.loc[past.course_id.eq(row.course_id), 'occupancy_rate']
        prior = float(past.occupancy_rate.mean()) if len(past) else .3
        valid = past[past.seats.gt(0) & past.occupancy_rate.notna()]
        if len(valid) and np.isfinite(row.seats) and row.seats > 0:
            weights = np.exp(-np.abs(np.log(valid.seats.to_numpy() / row.seats)))
            prior = float(np.average(valid.occupancy_rate, weights=weights))
        out.append((float(course.mean()) if len(course) else prior, len(course)))
    return pd.DataFrame(out, columns=['course_hist_mean', 'course_hist_n'], index=query.index)


@contextmanager
def using_history(fn):
    original = R.history
    R.history = fn
    try:
        yield
    finally:
        R.history = original


def evaluate(d, out, name, history_fn):
    per_room, frames = {}, []
    with using_history(history_fn):
        for room in sorted(d.room.unique()):
            available, query = d[d.room.ne(room)], d[d.room.eq(room)]
            assert set(available.room).isdisjoint(set(query.room))
            p, bundle, trials = R.fit_selected('LightGBM', available[available.week.lt(11)],
                                              available[available.week.eq(11)], available, query)
            met = R.metrics(query.occupancy_rate, p)
            per_room[room] = dict(rmse=met['rmse'], mae=met['mae'], n=len(query),
                                  setting=bundle['setting'], selection_trials=trials,
                                  reference_rooms=sorted(available.room.unique()))
            frames.append(R.prediction_frame(query, p))
            print(name, room, round(met['rmse'], 4), flush=True)
        it, ie = train_test_split(np.arange(len(d)), test_size=.2, random_state=R.SEED)
        itr, iv = train_test_split(it, test_size=.2, random_state=R.SEED)
        p, _, _ = R.fit_selected('LightGBM', d.iloc[itr], d.iloc[iv], d.iloc[it], d.iloc[ie])
        random_metrics = R.metrics(d.iloc[ie].occupancy_rate, p)
        R.prediction_frame(d.iloc[ie], p).to_csv(out / f'{name}_random_predictions.csv', index=False)
    frame = pd.concat(frames).sort_index()
    assert len(frame) == len(d) and frame.session_id.is_unique
    frame.to_csv(out / f'{name}_loro_predictions.csv', index=False)
    macro = float(np.mean([m['rmse'] for m in per_room.values()]))
    gap = macro / random_metrics['rmse'] - 1
    return dict(per_room=per_room, macro_rmse=macro, micro=R.metrics(frame.occupancy_rate, frame.prediction),
                random_split=random_metrics, gap_vs_random=gap,
                acceptance_pass=bool(macro <= .18 or gap <= .30))


def run():
    out = R.ROOT / '02、模型实验/生成产物/improvement_v3'
    out.mkdir(parents=True, exist_ok=True)
    d = R.load()
    report = {'experiment': 'improvement_v3', 'date': '2026-10-29',
              'status': 'Retrospective spatial comparison, not new blind or prospective validation.',
              'protocol': 'Same folds and LightGBM grid as revised; each method has its own random comparator.',
              'prior': 'Past sessions weighted by exp(-abs(log(reference_seats/query_seats))); no bandwidth search.',
              'limitations': ['Spatial training includes later dates from other rooms.',
                             'Repeated research on the same nine rooms; no independent new-room confirmation.',
                             'Session-weighted prior gives rooms with more historical sessions more influence.',
                             'v2 applied held-room band to training queries too; v3 uses each query capacity.'],
              'room_seats': {str(k): float(v) for k, v in d.groupby('room').seats.first().items()}}
    original = R.history
    with (out / 'run.log').open('w', encoding='utf-8') as log:
        class Tee:
            def write(self, s):
                sys.__stdout__.write(s)
                log.write(s)
            def flush(self):
                sys.__stdout__.flush()
                log.flush()
        with redirect_stdout(Tee()):
            for name, fn in [('global', original), ('continuous', capacity_history)]:
                report[name] = evaluate(d, out, name, fn)
            report['relative_macro_improvement'] = 1 - report['continuous']['macro_rmse'] / report['global']['macro_rmse']
            report['sha256'] = {str(p.relative_to(R.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [Path(__file__), Path(R.__file__), R.ROOT / '01、数据处理/清洗产物/sessions.csv']}
            R.dump(out / 'report.json', report)
            print(json.dumps({k: report[k]['macro_rmse'] for k in ['global', 'continuous']}))
    return report


if __name__ == '__main__':
    run()
