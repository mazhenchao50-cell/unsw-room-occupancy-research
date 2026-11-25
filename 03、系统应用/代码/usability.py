"""Summarize explicitly confirmed human trial records against the frozen trial protocol; no data means no score.

Task version trial_v7_20261124 (2026-11-24): course review and vacant-room candidate flows of the current app.
Criteria come only from 05、文档依赖/文档/usability/研究协议.json, whose SHA256 is written into the summary.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median, pstdev
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / '05、文档依赖/文档/usability/研究协议.json'
TASK_VERSION = 'trial_v7_20261124'
ANSWERS = {'T1': 'low_use_not_vacancy', 'T2': 'review_not_decision',
           'T3': 'candidate_needs_verification', 'T4': 'adjust_to_later'}
LANGUAGES = {'zh', 'en', 'ko', 'ja'}
CSV_COLUMNS = (['participant_id', 'observed_on', 'language', 'confirmed_human_trial']
               + [f'{tid}_{field}' for tid in ANSWERS for field in ('outcome', 'seconds', 'assisted', 'answer')]
               + [f'SUS{i}' for i in range(1, 11)] + ['notes'])


def load_protocol(path=PROTOCOL):
    path = Path(path); data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('task_version') != TASK_VERSION or {k: v['answer_code'] for k, v in data['tasks'].items()} != ANSWERS:
        raise ValueError('Trial protocol does not match this task version.')
    return data, hashlib.sha256(path.read_bytes()).hexdigest()


def sus_score(items):
    """Brooke (1996): odd items score-1, even items 5-score, sum x 2.5."""
    if not isinstance(items, list) or len(items) != 10 or any(type(x) is not int or not 1 <= x <= 5 for x in items):
        raise ValueError('sus must be ten integers from 1 to 5.')
    return 2.5 * sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(items))


def validate(record):
    if record.get('schema_version') != 2 or record.get('confirmed_human_trial') is not True:
        raise ValueError('Record must explicitly confirm a real human trial with schema_version=2.')
    participant = record.get('participant_id')
    if not isinstance(participant, str) or not participant.strip() or participant != participant.strip():
        raise ValueError('Anonymous participant_id required, without surrounding whitespace.')
    try:
        date.fromisoformat(record.get('observed_on', ''))
    except (ValueError, TypeError):
        raise ValueError('observed_on must be an actual trial date in YYYY-MM-DD format.') from None
    if record.get('language') not in LANGUAGES:
        raise ValueError('language must be one of zh, en, ko, ja.')
    if record.get('app_version') != TASK_VERSION:
        raise ValueError('app_version must be the current task version ' + TASK_VERSION + '.')
    if not isinstance(record.get('tasks'), list):
        raise ValueError('tasks must be a list.')
    seen = set()
    for task in record['tasks']:
        tid = task.get('task_id')
        if tid not in ANSWERS or tid in seen:
            raise ValueError('Unknown or duplicate task_id.')
        seen.add(tid)
        if task.get('outcome') not in ['completed', 'failed', 'abandoned']:
            raise ValueError('Invalid outcome.')
        seconds = task.get('duration_seconds')
        if type(seconds) not in [int, float] or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('duration_seconds must be a finite nonnegative number.')
        if type(task.get('assisted')) is not bool:
            raise ValueError('assisted must be true or false.')
        if task.get('answer_code') not in [ANSWERS[tid], 'incorrect', 'no_answer']:
            raise ValueError('Invalid answer_code.')
    if not seen:
        raise ValueError('No observed tasks; a blank template is not trial evidence.')
    sus_score(record.get('sus'))
    return record


def _bool(value, row, name):
    text = str(value).strip().lower()
    if text in ('yes', 'y', 'true', '1', '是'): return True
    if text in ('no', 'n', 'false', '0', '否'): return False
    raise ValueError(f'Row {row}: {name} must be yes or no.')


def load_csv(path):
    """One row per participant (记录表.csv). Rows without any value are ignored; empty task cells mean not observed."""
    records = []
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != CSV_COLUMNS:
            raise ValueError('Recording sheet columns must match usability.CSV_COLUMNS (use the shipped 记录表.csv).')
        for row_number, row in enumerate(reader, start=2):
            values = {k: (v or '').strip() for k, v in row.items() if k}
            if not any(values.values()):
                continue
            try:
                tasks = []
                for tid in ANSWERS:
                    if not values.get(f'{tid}_outcome'):
                        continue
                    tasks.append(dict(task_id=tid, outcome=values[f'{tid}_outcome'], duration_seconds=float(values[f'{tid}_seconds']),
                                      assisted=_bool(values[f'{tid}_assisted'], row_number, f'{tid}_assisted'), answer_code=values[f'{tid}_answer']))
                sus = [int(values[f'SUS{i}']) for i in range(1, 11)]
            except (KeyError, ValueError) as exc:
                raise ValueError(f'Row {row_number}: incomplete or malformed values ({exc}).') from None
            records.append(dict(schema_version=2, confirmed_human_trial=_bool(values.get('confirmed_human_trial', ''), row_number, 'confirmed_human_trial'),
                                participant_id=values.get('participant_id', ''), observed_on=values.get('observed_on', ''),
                                language=values.get('language', ''), app_version=TASK_VERSION, tasks=tasks, sus=sus, notes=values.get('notes', '')))
    return records


def summarize(records, protocol=None):
    seen = set(); rows = []; versions = set(); scores = []
    for raw in records:
        record = validate(raw)
        if record['participant_id'] in seen:
            raise ValueError('Duplicate participant_id; one record per participant required.')
        seen.add(record['participant_id'])
        versions.add(record['app_version'])
        if len(versions) > 1:
            raise ValueError('Different app versions must be summarized separately.')
        rows.extend(record['tasks']); scores.append(sus_score(record['sus']))
    def correct(t): return t['answer_code'] == ANSWERS[t['task_id']]
    def independent(t): return t['outcome'] == 'completed' and not t['assisted'] and correct(t)
    def metrics(tasks, expected):
        n = len(tasks); done = sum(t['outcome'] == 'completed' for t in tasks)
        understood = sum(correct(t) for t in tasks); alone = sum(independent(t) for t in tasks)
        return {'observed_tasks': n, 'expected_tasks': expected, 'completed': done, 'correct_understanding': understood,
                'independent_correct_completion': alone,
                'completion_rate': done / n if n else None, 'understanding_rate': understood / n if n else None,
                'independent_correct_completion_rate': alone / n if n else None,
                # Missing tasks count as not independently correct when judging the frozen criteria.
                'independent_correct_rate_over_expected': alone / expected if expected else None,
                'median_seconds_all_outcomes': median([t['duration_seconds'] for t in tasks]) if n else None}
    participants = len(seen)
    report = {'status': 'observations_collected' if rows else 'awaiting_human_trials', 'task_version': TASK_VERSION,
              'participants': participants, 'expected_tasks': 4 * participants, 'missing_tasks': 4 * participants - len(rows),
              'app_version': next(iter(versions)) if versions else None,
              'overall': metrics(rows, 4 * participants),
              'per_task': {tid: metrics([t for t in rows if t['task_id'] == tid], participants) for tid in ANSWERS},
              'sus': {'n': len(scores), 'mean': sum(scores) / len(scores) if scores else None, 'median': median(scores) if scores else None,
                      'sd': pstdev(scores) if len(scores) > 1 else None, 'scores': scores},
              'scope': 'Interface operation and interpretation only; not real classroom availability validation.'}
    if protocol is not None:
        c = protocol['success_criteria']
        if participants < c['min_participants']:
            report['criteria'] = {'status': 'insufficient_participants', 'met': None,
                                  'note': f"Fewer than {c['min_participants']} participants: observations only, no pass/fail judgement."}
        else:
            checks = {'overall_independent_correct': report['overall']['independent_correct_rate_over_expected'] >= c['overall_independent_correct_rate'],
                      'every_task_independent_correct': all(m['independent_correct_rate_over_expected'] >= c['per_task_independent_correct_rate'] for m in report['per_task'].values()),
                      'mean_sus': report['sus']['mean'] >= c['mean_sus']}
            report['criteria'] = {'status': 'evaluated', 'checks': checks, 'met': all(checks.values()), 'thresholds': c}
    return report


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--records-dir', type=Path, help='one JSON record per participant')
    source.add_argument('--records-csv', type=Path, help='记录表.csv, one row per participant')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=PROTOCOL)
    args = parser.parse_args()
    if args.records_dir is not None:
        if not args.records_dir.is_dir():
            parser.error('records-dir must be an existing directory')
        if args.output.resolve().parent == args.records_dir.resolve():
            parser.error('Keep output outside records-dir to avoid reading the summary as a participant.')
        records = [json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted(args.records_dir.glob('*.json'))]
    else:
        if not args.records_csv.is_file():
            parser.error('records-csv must be an existing file')
        records = load_csv(args.records_csv)
    protocol, digest = load_protocol(args.protocol)
    report = summarize(records, protocol)
    report['protocol_sha256'] = digest
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(report['status'], 'participants=', report['participants'], 'criteria=', (report.get('criteria') or {}).get('status'))


if __name__ == '__main__':
    main()
