"""Generate current human-readable reports from current JSON, never hand-copy scores."""
from pathlib import Path
import json,html
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
r=read('02、模型实验/生成产物/revised/report.json');q=read('01、数据处理/清洗产物/pipeline_report.json'); s=pd.read_csv(ROOT/'01、数据处理/清洗产物/sessions.csv')
out=ROOT/'05、文档依赖/文档/generated';out.mkdir(parents=True,exist_ok=True)
rows=[]
for name,m in r['time'].items():
    z=m['low_utilization']; rows.append({'模型':name,'RMSE':round(m['rmse'],4),'MAE':round(m['mae'],4),'低利用率Precision':round(z['precision'],4),'Recall':round(z['recall'],4),'F1':round(z['f1'],4),'预测阳性':z['predicted_positive']})
table=pd.DataFrame(rows)
def md_table(df):
    return '| '+' | '.join(map(str,df.columns))+' |\n|'+'---|'*len(df.columns)+'\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in df.itertuples(index=False,name=None))
card=f'''# 数据卡 修订版

本卡由 04、运行验证/代码/build_reports.py 从本轮报告生成。原始数据保持不变。

- 原始事件313044行，来源替换后310304行。week9文件10月2日删除2740行，其中2735条精确重复、5条按日期来源策略舍弃。
- 总会话{len(s)}，有效标签{s.occupancy_rate.notna().sum()}，所有实验排除week9后2360。匿名课程246个，教室9间，容量35至497。
- No-show 101/2361={101/2361:.2%}；低利用率422/2361={422/2361:.2%}；超员23/2361={23/2361:.2%}。上述比例分母均为有效标签会话。
- 标签是整节课峰值人数/座位数。低利用率<0.1，No-show实验标签为传感器推导的观测峰值人数=0，未逐条现场核验，超员>1。可共享和可使用还需开放权限、预约和现场占用证据。
- 出勤率仅在选课人数>0时计算；不将缺失置零。149条选课人数缺失仍保留，训练折内填充。
- 排课精确匹配1828行、未匹配530行、歧义4行。按日期、教室、完整起止时间many_to_one合并；歧义不猜测。
- 2017传感器范围为12周；2017考勤另有week13，2018仅考勤6周。原研究18周与本地12周传感器口径不同。
- 原始5个课程字段缺失819849/1565220={819849/1565220:.3%}。格式归一不等于缺失补全，没有“数据质量100分”结论。
- 本轮输入SHA256见01、数据处理/清洗产物/input_manifest.json；原下载日期、发布版校验值和许可证凭据仍待补充。
'''
(out/'data_card.md').write_text(card,encoding='utf-8')
protocol='''# 评估协议 v3

本轮是基于已看过数据的纠错与回顾性验证，不是预注册研究或新的盲测。未依据本轮测试成绩再调参。

第12周：w1–8训练、w10验证选参数、w11仅校准区间、w12测试。选定参数后用w1–8和w10固定参数重训，关闭早停。校准周不参加重训。P10/P90各自用w10选择树数，然后固定树数重训。

第8、10、11、12周滚动测试，每次最后两段分别作为验证周与校准周，训练只使用更早周。所有实验排除异常week9。

各学习算法统一8项基础特征和2项课程历史特征，不使用room编码；每算法3组候选。线性模型对alpha=0/1/10比较，选择正值时应称岭回归。SVR和线性模型标准化。各折只用训练数据填充；同日会话互不查看标签。课程历史按严格早于查询日期的训练会话聚合。未见课程回退此前参考样本全局均值，仅无过去样本时回退0.3。

LORO为纯空间诊断：留出整间教室、其他教室w11选参数后固定重训。其他教室可能包含未来日期，因此不宣称时间外推。Random split使用同一特征和3组参数；gap=(LORO macro RMSE-random RMSE)/random RMSE。另报告micro及相对时间测试差距，不混用分母。课程分组留出用于新课程诊断。

统一后处理仅下截断0，保留超过1的标签和预测。时间表static=选课人数/座位数；历史均值/中位数按教室×星期×上午分组，未见组回退训练均值；课程均值单独列为基线。四算法均报告去掉课程历史的消融。

低利用率阈值固定0.10。No-show独立以峰值人数=0建分类模型，树数40/100/200及概率阈值0.1/0.2/0.3/0.5仅在验证周选定。无课时段没有对应标签；课表空档不得当成无人。

区间仅在校准周按80%分位校正，先排序处理交叉，再评估测试覆盖。时间依赖破坏交换性，不能给未来覆盖保证。置信区间为按日期聚类的500次bootstrap；Precision附Wilson区间及阳性数，少量日期仍限制解释。

主验收沿用正式提交版数值：两个简单基线RMSE改善≥10%；低利用率F1≥0.60或Precision≥0.65；LORO教室均值≤0.18或相对随机差距≤30%。旧稿RF改善15%等为未达研究挑战目标，不替换正式门槛。术语及范围调整应交导师审阅。
'''
(out/'evaluation_protocol.md').write_text(protocol,encoding='utf-8')
summary='# 本轮实验结果\n\n本表是回顾性重算；低利用率不等于无人。\n\n'+md_table(table)+f"\n\nLORO micro RMSE={r['loro']['micro']['rmse']:.4f}，macro={r['loro']['macro_rmse']:.4f}，相对Random split差距={r['loro']['macro_gap_vs_random']:.2%}。\n\n名义80%区间实测覆盖={r['quantiles']['coverage']:.2%}。No-show Precision={r['no_show']['metrics']['precision']:.4f}，F1={r['no_show']['metrics']['f1']:.4f}，尚不适合自动释放教室。\n"
(out/'revision_results.md').write_text(summary,encoding='utf-8')
css='<style>body{max-width:1100px;margin:36px auto;padding:0 20px;font:17px/1.65 system-ui;color:#18222d}table{border-collapse:collapse;width:100%;margin:24px 0}td,th{border:1px solid #ccd4dc;padding:8px;text-align:left}th{background:#edf2f6}h1,h2{line-height:1.3}.scroll{overflow:auto}li{margin:8px 0}</style>'
bins=[]
y=s.occupancy_rate.dropna()
for i in range(10):bins.append({'区间':f'{i*10}–{(i+1)*10}%' + ('（含100%）' if i==9 else '（右开）'),'会话数':int(((y>=i/10)&((y<((i+1)/10)) if i<9 else y.le(1))).sum())})
bins.append({'区间':'>100%','会话数':int(y.gt(1).sum())});assert sum(x['会话数'] for x in bins)==len(y)
rooms=s.groupby('room').size().rename('总会话').reset_index()
page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+css+'<h1>处理后数据集说明</h1><p>2362总会话，2361有效标签，2360实验纳入。缺失不能当成零占用。</p><h2>教室统计</h2>'+rooms.to_html(index=False)+'<h2>占用率分箱</h2>'+pd.DataFrame(bins).to_html(index=False)+'<p>分箱合计2361，完整计入恰好100%的4条样本。数据处理及残留问题见data_card.md。</p>'
(out/'处理后数据集说明.html').write_text(page,encoding='utf-8')
page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+css+'<h1>项目修订进度与验收</h1><p>进度以实际证据列示，取消手工百分比估算。</p><ul><li>数据管道：完成修订并重建，仍保留缺失及匹配不确定状态。</li><li>模型：完成时间、空间、新课程、消融和区间重算；部分性能门槛未达。</li><li>演示：历史回放、课表冲突过滤、Top5候选及独立No-show风险。</li><li>行政：导师签字角色、报销资格和提交凭据待真实确认。</li></ul><h2>第12周结果</h2><div class="scroll">'+table.to_html(index=False)+'</div><p>准确含义见evaluation_protocol.md。不能用低利用率Precision证明教室真正无人。</p>'
(out/'progress_dashboard.html').write_text(page,encoding='utf-8')
readme='''# 教室占用预测与历史回放 修订版

当前重建入口为 04、运行验证/代码/run_all.py，当前结果在 02、模型实验/生成产物/revised。旧phase2/3/4及备份文件只作历史留档，不能引用其结论作为当前成果。正式课题名称保留，产品界面准确使用低利用率和课表空档候选。

## 从零运行

本机使用 Python 3.13.7 的 `.venv-repro`；锁定依赖见 05、文档依赖/依赖/requirements-windows-py313.lock。其他平台和 Python 版本需单独验证。

```powershell
python -m venv .venv-repro
.venv-repro\\Scripts\\python.exe -m pip install -r "05、文档依赖\\依赖\\requirements-windows-py313.lock"
.venv-repro\\Scripts\\python.exe "04、运行验证\\代码\\run_all.py" --profile core
.venv-repro\\Scripts\\python.exe -m streamlit run "03、系统应用\\代码\\app.py" --client.toolbarMode minimal
```

模型、逐样本预测、SHAP矩阵及网页、质量报告、输入SHA256和运行环境均由脚本生成。界面限定第12周历史回放；候选的现场占用和开放权限未知。课程被排课占用时，即使预测低利用率也不能推荐使用。

## 结果及边界

'''+summary.replace('# 本轮实验结果','')+'''

完整口径见05、文档依赖/文档/evaluation_protocol.md，数据见05、文档依赖/文档/data_card.md。推荐回放检查结果见02、模型实验/生成产物/revised/replay_report.json，2018独立考勤诊断见transfer2018_report.json。2018诊断不等于主传感器模型跨学期验证。天气尚未采集，当前模型不使用天气；不会将没有的消融或现场验证写成完成。

## 验证

```powershell
.venv-repro\\Scripts\\python.exe -m unittest discover -s "04、运行验证\\测试" -v
.venv-repro\\Scripts\\python.exe "04、运行验证\\测试\\test_app.py"
```

历史版本在项目根目录11、导师反馈修订（2026-10-13）/原版备份。原始CSV和已提交HWP保留；新的修订报告和韩文更正稿用于重新送审，未声称已经替换校方提交版本。
'''
(out/'README_baseline.md').write_text('本文件为自动生成的主实验快照。命令从项目实施根目录运行；当前导航见 05、文档依赖/文档/项目实施目录说明.md。\n\n'+readme,encoding='utf-8')
for phase in ['phase2_baselines','phase3_lightgbm','phase4_shap']:
    if (ROOT/'02、模型实验/生成产物'/phase).exists():
        (ROOT/'02、模型实验/生成产物'/phase/'历史版本说明.md').write_text('本目录是修订前历史产物，包含已被审核指出的问题，不作为当前结论。主实验结果目录为 ../revised；后续实验单独标注。',encoding='utf-8')
print('Generated baseline snapshots under 05、文档依赖/文档/generated; curated README and protocol preserved')
