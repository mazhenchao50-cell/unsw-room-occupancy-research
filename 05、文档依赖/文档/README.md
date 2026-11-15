# 教室占用预测与历史回放 修订版

当前代码、运行输入和输出的文件夹分工见 [项目实施目录说明](项目实施目录说明.md)。14 个原始 UNSW CSV 位于 `01、数据处理/原始数据/UNSW/`；当前命令和安装说明见 [安装与复现说明](reproduction.md)。以下 L029 及更早记录是历史快照，其中旧路径不再作为当前操作命令。

## 当前运行入口

所有命令在 `8、项目实施（预测与推荐）` 执行；初次安装依赖见上述安装说明。

```powershell
.venv-repro\Scripts\python.exe "04、运行验证\代码\run_all.py" --profile core
.venv-repro\Scripts\python.exe -m streamlit run "03、系统应用\代码\app.py"
# 完整独立副本重建，包含当前扩展实验及四语检查
.venv-repro\Scripts\python.exe "04、运行验证\代码\verify_reproduction.py" --profile extended
```

当前验收读取 `02、模型实验/生成产物/acceptance/status.json`。本地源码可复现与GitHub发布是不同证据，目前没有已验证的GitHub端发布/第三方复现记录。下面历史记录中的旧命令不得直接用于当前目录。

已有清洗产物时，可直接运行上面第二条命令。首次体验可用默认的2017-10-16、09:00、60分钟、10个座位，选择候选教室并保存演示核查单。查询以历史课表为依据，现场使用须另核对当天课表、预约和开放权限。

要检查单次占用率预测，在侧栏开启研究详情，找到“查看某节课的预测依据”，选择当前时段课程。表格显示实际模型输入和各因素的贡献百分点，摘要提供模型基准、贡献合计、原始预测及显示值。默认模式与统一研究模式的已见教室分支均支持这项检查。

扩展重建后，在侧栏打开“显示预测与研究验证详情”即可切换预测方案。研究方案按教室是否在拟合名单中选择预测方法。验收JSON的 `items` 是默认模式，`integrated_research_evidence` 是统一研究模式。四项目标及论文数值对照见两本Word的L038与L039，对应计算依据为 `02、模型实验/生成产物/acceptance/comparison.json`。

项目叙述性进度从2026年11月5日起只同步写入两份Word：`../4、项目确认（项目构思白皮书）/最终白皮书（Word）/专业版_项目白皮书与全程记录.docx`与`大白话版_项目白皮书与全程记录.docx`。本README和`PROJECT_STATUS.md`保留为当时的软件导航与历史快照；实验JSON、测试日志和数据哈希继续作为原始证据。

## 当前环境与复现入口 L029

当前工作区原`.venv`不存在，已重新安装独立`.venv-repro`（Windows x64 / Python 3.13.7）。现有模型在该环境中的中英韩日界面检查通过。当前启动命令：

```powershell
.venv-repro\Scripts\python.exe -m streamlit run "03、系统应用\代码\app.py"
```

首次安装、完整版本清单和不覆盖原结果的复现方法见 [安装与复现说明](reproduction.md)。使用 `04、运行验证/代码/verify_reproduction.py` 可在不带旧产物的源码副本中重建；完整结果以该次 `verification.json` 为准。以下L028及更早记录中的`.venv`命令是历史环境路径，不代表该环境目前仍存在。

L029实测：新依赖环境完整extended重建通过，32项测试、240查询和四语检查通过。处理后会话和三个预测CSV与原文件字节一致。证据：`logs/reproduction_20261104T145150057865Z/verification.json`及`comparison.json`。这是本机新环境复现，不是新机器或跨平台保证。

## L028 按根因修复与复核

本轮将缺失输入、未初始化产物和可选产物依赖作为共同原因处理：`run_all.py`在执行前列出全部缺失/空输入；运行中按阶段保存UTF-8日志，首个失败后停止。日志与退出码保存在 `logs/rebuild_*/execution.json`，应从第一处失败检查，不应直接继续执行下游脚本或删除原始数据。

界面缺少必要产物时显示四语初始化提示。维护者从本目录执行 `.venv\Scripts\python.exe run_all.py --profile core`，成功后重新启动界面；缺少UCI和v5可选实验不会阻止核心界面。界面测试已覆盖有/无扩展面板及缺少核心产物三类场景。

32项单元测试全部通过，四语正常交互与初始化提示通过。沙箱临时目录权限失败经过沙箱外原测试复核，不能误写成模型故障。详细证据和剩余边界见 `PROJECT_STATUS.md` 与白皮书L028续记。

## L027 证据边界与复现修正

当前状态与优先级见 [PROJECT_STATUS.md](PROJECT_STATUS.md)。已补记L026的No-show候选：合计误报93降至45，但周间不稳定，未替换现用模型。L027发现101条观测零峰值均未与考勤表精确匹配，标签仅视作传感器推导的代理标签，不能直接当作已现场确认的无人课程。

本轮修复异常课表时段筛选、核心流程依赖扩展旧产物、自动报告覆盖人工协议三个问题。自动快照现在写入 `docs/generated/`。核心检查29通过、2项扩展产物检查明确跳过；240历史查询和四语交互通过。完整独立环境重建仍未完成。

主实验重建使用 `run_all.py --profile core`；包括UCI和v5候选使用 `--profile extended`，缺UCI源文件时额外指定 `--download-external`。`--dry-run`仅列计划。直接运行全部unittest默认会包含扩展产物检查，需要已生成UCI及v5产物；核心路线由run_all设置相应测试范围。

## L025 多语言与真实数据

左侧 Language / 언어 / 语言 / 言語 可切换中文、English、한국어、日本語，查询参数保持不变。候选、状态、错误提示、预测及SHAP表均随语言切换。翻译目录为 `src/i18n.py`，可继续扩展语言。

无需上传本校数据或用户试用记录即可运行。现有UNSW公开真实数据继续用于主实验；本轮已额外下载UCI公开真实办公室占用数据及官方许可快照，完成单独的当前占用检测验证，见 `results/external_uci/report.json`。该结果不替代主模型、未来预测、本校或现场可用性验证。

重要纠正：原提交版第④项没有将真实用户试用或本校数据采集列为必选门槛。此前L023/L024将试用作为推进前提的表述过严，现按原要求分别检查流程、SHAP、No-show意义与复现。真实试用保留为可选补强。No-show实用性和全新环境/GitHub复现仍有不足，不能据此宣布整体验收通过。详细依据见 `docs/真实数据与验收依据_20261031.md`。

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
# 使用已下载的真实数据，离线重跑补充实验和功能检查
.venv\Scripts\python.exe src/models/external_uci.py
.venv\Scripts\python.exe src/validate_system.py
```

系统功能证据：240个UNSW历史查询场景通过；中英韩日交互检查通过；22项单元测试通过。参见 `results/system/`。UCI独立检测：训练8143条、未来时段测试9752条，准确率98.51%，无人检测F1=99.06%，仍有93条有人记录误判为无人。所有指标须连同场景边界引用。

当前入口为run_all.py，当前结果在results/revised。旧phase2/3/4及备份文件只作历史留档，不能引用其结论作为当前成果。正式课题名称保留，产品界面准确使用低利用率和课表空档候选。

2026-10-29：白皮书 L021 后续的连续座位数加权先验实验已完成，见 `results/improvement_v3/report.json`；运行 `.venv\Scripts\python.exe src/models/improvement_v3.py` 可复现。LORO macro 从重跑基线 0.227924 降至 0.217556（改善4.55%），与该方法自身随机切分的差距为63.98%，冷启动指标仍未达。此实验单独保存，尚未替换演示模型。完整解释及历史记录勘误见项目根目录 `4、项目确认（项目构思白皮书）/白皮书续记_L022_20261029.md`。下方表格仍为 revised 原始固定阈值结果；阈值调优结果另见 improvement_v1。

## 从零运行

2026-10-31：L023两周本教室历史适应实验已完成。第11、12周同一批415条测试记录上，macro RMSE从0.220725降至0.190042（改善13.90%）；4间教室改善、5间退步。全部测试课程在适应期已出现，不代表新课程有效，也不改变纯冷启动指标未达状态。结果在 `results/improvement_v4/report.json`，运行 `.venv\Scripts\python.exe src/models/improvement_v4.py` 可复现；完整续记在项目根目录 `4、项目确认（项目构思白皮书）/白皮书续记_L023_20261031.md`。本轮实验未替换当前演示模型。

本机验证环境Python 3.14.7；建议Python 3.14，依赖固定版本见requirements.txt。其他Python版本与全新机器安装尚未实测。

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run_all.py --data-dir "data\raw\unsw"
.venv\Scripts\python.exe -m streamlit run app.py
```

模型、逐样本预测、SHAP矩阵及网页、质量报告、输入SHA256和运行环境均由脚本生成。界面限定第12周历史回放；候选的现场占用和开放权限未知。课程被排课占用时，即使预测低利用率也不能推荐使用。

## 结果及边界



本表是回顾性重算；低利用率不等于无人。

| 模型 | RMSE | MAE | 低利用率Precision | Recall | F1 | 预测阳性 |
|---|---|---|---|---|---|---|
| historical_mean | 0.1863 | 0.1537 | 1.0 | 0.0714 | 0.1333 | 4 |
| historical_median | 0.1865 | 0.1444 | 0.8571 | 0.1071 | 0.1905 | 7 |
| course_history_mean | 0.1472 | 0.1119 | 1.0 | 0.2857 | 0.4444 | 16 |
| timetable_static | 0.5398 | 0.4218 | 0.4 | 0.0714 | 0.1212 | 10 |
| LightGBM | 0.1471 | 0.1002 | 0.5962 | 0.5536 | 0.5741 | 52 |
| RF | 0.1133 | 0.0751 | 0.6591 | 0.5179 | 0.58 | 44 |
| MLR | 0.1228 | 0.0866 | 0.6066 | 0.6607 | 0.6325 | 61 |
| SVR | 0.1196 | 0.0821 | 0.75 | 0.5357 | 0.625 | 40 |

LORO micro RMSE=0.2355，macro=0.2279，相对Random split差距=67.37%。

名义80%区间实测覆盖=75.24%。No-show Precision=0.0674，F1=0.1224，尚不适合自动释放教室。


完整口径见docs/evaluation_protocol.md，数据见docs/data_card.md。推荐回放检查结果见results/revised/replay_report.json，2018独立考勤诊断见transfer2018_report.json。2018诊断不等于主传感器模型跨学期验证。天气尚未采集，当前模型不使用天气；不会将没有的消融或现场验证写成完成。

## 验证

2026-10-31 L024：界面已补充中文状态、无候选说明与跨午夜校验；自动交互检查通过。真实试用指南见 `docs/usability/试用执行指南.md`，空白记录模板见同目录 `record_template.json`。真实记录放入 `docs/usability/records/` 后，可运行 `.venv\Scripts\python.exe src/usability.py --records-dir docs/usability/records --output results/usability/summary.json` 汇总。目前参与者为0，可用性仍待验证，不能将自动检查作为真实试用证据。

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tests/test_app.py
```

历史版本在项目根目录11、导师反馈修订（2026-10-13）/原版备份。原始CSV和已提交HWP保留；新的修订报告和韩文更正稿用于重新送审，未声称已经替换校方提交版本。
