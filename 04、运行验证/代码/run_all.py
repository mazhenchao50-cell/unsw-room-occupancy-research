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
        calendar=Path(os.environ.get('UNSW_CALENDAR_DIR',str(ROOT.parent/'11、运行环境与验证存档（原D盘）/2、外部来源证据/学期日历原件_20261117')))
        required += [calendar/name for name in ('UNSW_TABL2751_2017.pdf','NSW_Parliament_2017_Calendar.pdf')]
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

def build_commands(data_dir,profile='standard',download_external=False):
    commands=[['01、数据处理/代码/pipeline_clean.py','--data-dir',str(data_dir)],['02、模型实验/代码/models/revised.py'],
        ['02、模型实验/代码/models/transfer_diagnostic.py'],['02、模型实验/代码/models/explain_revised.py'],['03、系统应用/代码/replay.py'],
        ['04、运行验证/代码/build_reports.py'],['04、运行验证/代码/audit_labels.py'],['04、运行验证/代码/validate_system.py']]
    if profile=='standard':
        commands.append(['02、模型实验/代码/models/unified.py'])
    if profile=='extended':
        if download_external:
            directory=os.environ.get('UNSW_DOWNLOAD_DIR')
            if not directory:raise ValueError('Set UNSW_DOWNLOAD_DIR explicitly; downloads must not use the system drive by accident')
            commands.insert(0,['04、运行验证/代码/acquire_supporting.py','--download-dir',directory])
        commands.extend([['02、模型实验/代码/models/external_uci.py']+(['--download'] if download_external else []),
                         ['02、模型实验/代码/models/improvement_v3.py'],
                         ['02、模型实验/代码/models/improvement_v4.py'],
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
        commands.extend([
            ['02、模型实验/补充研究/01、双分类器共识/代码/recompute_consensus.py'],
            ['02、模型实验/补充研究/02、漏报与跨周稳定性/代码/stable_alerts.py','--cache-root',
             str(ROOT/'02、模型实验/补充研究/02、漏报与跨周稳定性/生成产物/模型')],
            ['02、模型实验/补充研究/03、稳定概率与阈值校准/代码/bounded_calibration.py'],
            ['02、模型实验/补充研究/04、日历背景与固定分类/代码/calendar_replay.py'],
            ['04、运行验证/代码/audit_diagnostics.py','--models'],
            ['02、模型实验/补充研究/05、成本敏感与无报名冷启动/代码/resolve_models.py','--task','all'],
            ['02、模型实验/补充研究/06、早期校准后固定阈值/代码/fixed_policy.py'],
            ['02、模型实验/补充研究/07、回归分类联合复核/代码/joint_review.py'],
            ['02、模型实验/补充研究/08、三模型固定多数决/代码/majority.py'],
            ['02、模型实验/补充研究/09、日历情境历史/代码/context_history.py'],
            ['02、模型实验/补充研究/10、保留原提示的情境补充/代码/context_supplement.py'],
            ['02、模型实验/补充研究/11、空间冷启动余量/代码/spatial_margin.py']])
        commands.append(['02、模型实验/补充研究/12、指标口径与边界复核/代码/metric_review.py'])
        commands.append(['02、模型实验/补充研究/13、回归口径空教室筛选/代码/regression_screen.py'])
        commands.append(['02、模型实验/补充研究/13、回归口径空教室筛选/代码/label_semantics.py'])
        commands.append(['02、模型实验/补充研究/14、两段式占用率模型/代码/two_part.py'])
        # 2026-11-24 复核实验：惯性基线、2018外部验证、报名泄漏敏感性、正式模型SHAP、无课时段空教室
        commands.append(['02、模型实验/补充研究/15、惯性基线与显著性检验/代码/persistence.py'])
        commands.append(['02、模型实验/补充研究/16、2018未见学期外部验证/代码/holdout_2018.py'])
        commands.append(['02、模型实验/补充研究/17、报名人数泄漏敏感性/代码/no_enrollment.py'])
        commands.append(['02、模型实验/补充研究/17、报名人数泄漏敏感性/代码/tolerance.py'])
        commands.append(['02、模型实验/补充研究/18、正式模型SHAP解释/代码/explain_v6.py'])
        commands.append(['02、模型实验/补充研究/19、无课时段空教室识别/代码/free_slots.py'])
        # 2026-11-24 二次复查：严格前推留一教室、同等信息对比、延续在室人数
        commands.append(['02、模型实验/补充研究/20、严格前推留一教室/代码/forward_loro.py'])
        commands.append(['02、模型实验/补充研究/16、2018未见学期外部验证/代码/equal_info.py'])
        commands.append(['02、模型实验/补充研究/19、无课时段空教室识别/代码/carryover.py'])
        # 2026-11-24 三次复查：两段式第一段概率校准（未采用）
        commands.append(['02、模型实验/补充研究/23、两段式概率校准/代码/calibrate_two_part.py'])
    if profile in ('standard','extended'):
        commands.append(['04、运行验证/代码/numeric_acceptance.py'])
        commands.append(['04、运行验证/代码/audit_project.py','--runtime'])
    commands.append(['04、运行验证/代码/run_tests.py'])
    commands.append(['04、运行验证/测试/test_app.py'])
    commands.append(['04、运行验证/代码/build_release.py'])
    commands.append(['04、运行验证/代码/build_acceptance.py'])
    return commands

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data-dir',type=Path,default=ROOT/'01、数据处理/原始数据/UNSW')
    p.add_argument('--profile',choices=['core','standard','extended'],default='standard')
    p.add_argument('--download-external',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--formal-only',action='store_true',help='Only rebuild raw cleaning, the formal model and numeric inference checks; not a full validation')
    args=p.parse_args()
    if args.download_external and os.environ.get('UNSW_DOWNLOAD_DIR'):
        os.environ.setdefault('UNSW_CALENDAR_DIR',os.environ['UNSW_DOWNLOAD_DIR'])
    if args.download_external and args.profile!='extended':
        p.error('--download-external requires --profile extended')
    commands=build_commands(args.data_dir.resolve(),args.profile,args.download_external)
    if args.formal_only:
        if args.download_external:p.error('--formal-only does not run external experiments')
        commands=[['01、数据处理/代码/pipeline_clean.py','--data-dir',str(args.data_dir.resolve())],
            ['02、模型实验/代码/models/unified.py'],['04、运行验证/代码/numeric_acceptance.py']]
    if args.dry_run:
        print(json.dumps({'profile':args.profile,'commands':commands},ensure_ascii=False,indent=2));return
    missing=missing_inputs(args.data_dir.resolve(),'core' if args.formal_only else args.profile,args.download_external)
    if missing:
        p.error('Required inputs missing or empty (no stages run):\n'+'\n'.join(missing)+
                '\nCheck --data-dir; for missing UCI sources use --profile extended --download-external.')
    return execute_commands(commands,'formal_only' if args.formal_only else args.profile)

if __name__=='__main__':sys.exit(main())
