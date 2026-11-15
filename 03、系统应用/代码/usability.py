"""Summarize explicitly confirmed human trial records; no data means no score."""
import argparse
import json
import math
from pathlib import Path
from statistics import median
from datetime import date

ANSWERS = {'T1':'needs_verification', 'T2':'no_candidate_not_proof',
           'T3':'scheduled_room_blocked', 'T4':'adjust_interval'}


def validate(record):
    if record.get('schema_version') != 1 or record.get('confirmed_human_trial') is not True:
        raise ValueError('Record must explicitly confirm a real human trial with schema_version=1.')
    participant = record.get('participant_id')
    if not isinstance(participant,str) or not participant.strip():
        raise ValueError('Anonymous participant_id required.')
    if participant != participant.strip():
        raise ValueError('participant_id must not have surrounding whitespace.')
    try:
        date.fromisoformat(record.get('observed_on',''))
    except (ValueError,TypeError):
        raise ValueError('observed_on must be an actual trial date in YYYY-MM-DD format.') from None
    if not isinstance(record.get('app_version'),str) or not record['app_version'].strip():
        raise ValueError('app_version required.')
    if not isinstance(record.get('tasks'),list):
        raise ValueError('tasks must be a list.')
    seen=set()
    for task in record['tasks']:
        tid=task.get('task_id')
        if tid not in ANSWERS or tid in seen:
            raise ValueError('Unknown or duplicate task_id.')
        seen.add(tid)
        if task.get('outcome') not in ['completed','failed','abandoned']:
            raise ValueError('Invalid outcome.')
        seconds=task.get('duration_seconds')
        if type(seconds) not in [int,float] or not math.isfinite(seconds) or seconds<0:
            raise ValueError('duration_seconds must be a finite nonnegative number.')
        if type(task.get('assisted')) is not bool:
            raise ValueError('assisted must be true or false.')
        if task.get('answer_code') not in [ANSWERS[tid], 'incorrect', 'no_answer']:
            raise ValueError('Invalid answer_code.')
    if not seen:
        raise ValueError('No observed tasks; a blank template is not trial evidence.')
    return record


def summarize(records):
    seen=set(); rows=[]; versions=set()
    for raw in records:
        record=validate(raw)
        if record['participant_id'] in seen:
            raise ValueError('Duplicate participant_id; one record per participant required.')
        seen.add(record['participant_id'])
        versions.add(record['app_version'])
        if len(versions)>1:
            raise ValueError('Different app versions must be summarized separately.')
        rows.extend(record['tasks'])
    def metrics(tasks):
        n=len(tasks)
        completed=sum(t['outcome']=='completed' for t in tasks)
        understood=sum(t['answer_code']==ANSWERS[t['task_id']] for t in tasks)
        independent=sum(t['outcome']=='completed' and not t['assisted'] and
                        t['answer_code']==ANSWERS[t['task_id']] for t in tasks)
        return {'observed_tasks':n, 'completed':completed, 'correct_understanding':understood,
                'independent_correct_completion':independent,
                'completion_rate':completed/n if n else None,
                'understanding_rate':understood/n if n else None,
                'independent_correct_completion_rate':independent/n if n else None,
                'median_seconds_all_outcomes':median([t['duration_seconds'] for t in tasks]) if n else None}
    return {'status':'observations_collected' if rows else 'awaiting_human_trials',
            'participants':len(seen), 'expected_tasks':4*len(seen),
            'app_version':next(iter(versions)) if versions else None,
            'missing_tasks':4*len(seen)-len(rows), 'overall':metrics(rows),
            'per_task':{tid:metrics([t for t in rows if t['task_id']==tid]) for tid in ANSWERS},
            'acceptance':'Not automatically awarded. Review sample size, missing tasks, errors and participant feedback.',
            'scope':'Interface operation and interpretation only; not real classroom availability validation.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--records-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.records_dir.is_dir():
        parser.error('records-dir must be an existing directory')
    if args.output.resolve().parent==args.records_dir.resolve():
        parser.error('Keep output outside records-dir to avoid reading the summary as a participant.')
    records=[json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted(args.records_dir.glob('*.json'))]
    report=summarize(records)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(report['status'], 'participants=',report['participants'])


if __name__=='__main__':
    main()
