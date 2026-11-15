"""Rebuild primary outputs; optional experiments are an explicit extended profile."""
from pathlib import Path
import subprocess,sys,argparse,os,json
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]

def missing_inputs(data_dir, profile, download_external=False):
    required=[Path(data_dir)/f'{year}_sem2_attendance_data.csv' for year in (2017,2018)]
    required += [Path(data_dir)/f'week{week}_computed_data.csv' for week in range(1,13)]
    if profile=='extended' and not download_external:
        required += [ROOT/'01、数据处理/原始数据/UCI'/f for f in ('occupancy_detection.zip','source.html')]
    return [str(path) for path in required if not path.is_file() or path.stat().st_size==0]

def execute_commands(commands, profile):
    """Stop at the first failed stage and preserve its log instead of cascading errors."""
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'04、运行验证/日志'/f'rebuild_{stamp}';out.mkdir(parents=True)
    report={'profile':profile,'python':sys.executable,'status':'running','stages':[]}
    def save():
        (out/'execution.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    env=os.environ.copy();env.update(PROJECT_TEST_PROFILE=profile,PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    env['PYTHONPATH']=os.pathsep.join([str(ROOT/'02、模型实验/代码'),str(ROOT/'03、系统应用/代码'),str(ROOT/'04、运行验证/代码'),env.get('PYTHONPATH','')])
    save()
    for index,command in enumerate(commands,1):
        log=out/f'{index:02d}.log'
        print('RUN',command,'LOG',log,flush=True)
        stage={'command':command,'log':str(log.relative_to(ROOT))}
        report['stages'].append(stage)
        try:
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run([sys.executable,'-u',*command],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
            stage['returncode']=result.returncode
        except OSError as exc:
            stage.update(returncode=1,error=str(exc))
        if stage['returncode']:
            report['status']='failed';save()
            print(f'FAILED at stage {index}; later stages were not run. See {log}',file=sys.stderr)
            return stage['returncode']
        save()
    report['status']='passed';save()
    print('PASS: requested stages completed. Evidence:',out,flush=True)
    return 0

def build_commands(data_dir,profile='core',download_external=False):
    commands=[['01、数据处理/代码/pipeline_clean.py','--data-dir',str(data_dir)],['02、模型实验/代码/models/revised.py'],
        ['02、模型实验/代码/models/transfer_diagnostic.py'],['02、模型实验/代码/models/explain_revised.py'],['03、系统应用/代码/replay.py'],
        ['04、运行验证/代码/build_reports.py'],['04、运行验证/代码/audit_labels.py'],['04、运行验证/代码/validate_system.py']]
    if profile=='extended':
        commands.extend([['02、模型实验/代码/models/external_uci.py']+(['--download'] if download_external else []),
                         ['02、模型实验/代码/models/improvement_v5.py'],
                         ['02、模型实验/代码/models/improvement_v6.py'],
                         ['02、模型实验/代码/models/improvement_v7.py'],
                         ['02、模型实验/代码/models/improvement_v8.py'],
                         ['02、模型实验/代码/models/improvement_v9.py'],
                         ['02、模型实验/代码/models/improvement_v10.py'],
                         ['02、模型实验/代码/models/improvement_v11.py'],
                         ['02、模型实验/代码/models/unified.py'],
                         ['02、模型实验/代码/models/risk_review.py'],
                         ['02、模型实验/代码/models/forward_cold_benchmark.py']])
    commands.append(['-m','unittest','discover','-s','04、运行验证/测试','-v'])
    commands.append(['04、运行验证/代码/build_release.py'])
    commands.append(['04、运行验证/代码/build_acceptance.py'])
    return commands

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data-dir',type=Path,default=ROOT/'01、数据处理/原始数据/UNSW')
    p.add_argument('--profile',choices=['core','extended'],default='core')
    p.add_argument('--download-external',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    if args.download_external and args.profile!='extended':
        p.error('--download-external requires --profile extended')
    commands=build_commands(args.data_dir.resolve(),args.profile,args.download_external)
    if args.dry_run:
        print(json.dumps({'profile':args.profile,'commands':commands},ensure_ascii=False,indent=2));return
    missing=missing_inputs(args.data_dir.resolve(),args.profile,args.download_external)
    if missing:
        p.error('Required inputs missing or empty (no stages run):\n'+'\n'.join(missing)+
                '\nCheck --data-dir; for missing UCI sources use --profile extended --download-external.')
    return execute_commands(commands,args.profile)

if __name__=='__main__':sys.exit(main())
