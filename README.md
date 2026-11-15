# 教室占用预测与历史回放

本项目研究UNSW公开历史数据中的课程峰值占用率。支持中英韩日界面，输出课表空档候选；不证明现场无人或使用许可。研究分数为回顾性结果，原验收仍有未达项目。

## 文件组织

01、数据处理含清洗代码；02、模型实验含模型与独立实验；03、系统应用含界面、翻译、历史回放；04、运行验证含重建与测试；05、文档依赖含安装说明与固定依赖。

## Windows安装与运行

使用Python 3.13，以下命令在解压后的仓库根目录执行。其他系统和版本尚未验证。

```powershell
$env:TEMP='D:\ProjectTools\UNSW_Reproduction\tmp'
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR='D:\ProjectTools\UNSW_Reproduction\cache'
New-Item -ItemType Directory -Force -Path $env:TEMP,$env:PIP_CACHE_DIR | Out-Null
python -m venv 'D:\ProjectTools\UNSW_Reproduction\.venv'
& 'D:\ProjectTools\UNSW_Reproduction\.venv\Scripts\python.exe' -m pip install -r "05、文档依赖\依赖\requirements-windows-py313.lock"
& 'D:\ProjectTools\UNSW_Reproduction\.venv\Scripts\python.exe' "04、运行验证\代码\run_all.py" --profile core
& 'D:\ProjectTools\UNSW_Reproduction\.venv\Scripts\python.exe' -m streamlit run "03、系统应用\代码\app.py"
```

## 原始数据前置条件

发布准备包不含原始数据、训练结果、虚拟环境和运行日志。UNSW原始数据的再分发许可尚未核实，不能随源码包公开上传。数据取得与对应许可必须另行确认，本包不宣称在没有原始输入时可以直接重建。

本地已有合法数据时，在01、数据处理/原始数据/UNSW放入2017_sem2_attendance_data.csv、2018_sem2_attendance_data.csv及week1_computed_data.csv至week12_computed_data.csv，共14份。预期内容哈希见data_requirements.json。文件不符时先核查数据版本，不能假定原分数仍然成立。

数据身份已做过逐文件核验：2026-11-11从[UNSW Smart Campus官方数据页](https://smartcampus.unsw.edu.au/roomoccupancy/index.html)下载的[data.zip](https://smartcampus.unsw.edu.au/roomoccupancy/data.zip)中恰有这14份CSV，均与本地原件SHA256逐项相同；这不是随机找来的14个文件或截取的样本。核验明细保存在项目内部的04、运行验证/日志/unsw_source_20261111/官方来源核对.json。[2019年论文](https://doi.org/10.1109/JIOT.2019.2902410)称该周度数据集可下载，但本项目尚未核实数据的再分发许可；因此发布包不含CSV，使用者需从官方来源自行取得并按data_requirements.json核验。若官方入口失效或哈希不符，应暂停重建并联系数据维护方，不要用相似数据替代。

本项目范围明确限定为UNSW特定教室的历史数据研究；当前不收集本校真实数据，也不据此声称本校适用或完成独立校园验证。若未来另立本校应用研究，须由校方数据管理方批准，取得覆盖多教室和多个教学周的课程时间、教室容量与课程级峰值人数/占用观测，并先明确来源、授权和留出方案。只收集分析必需的聚合字段，不收集学生姓名、学号或视频。授权、隐私审查或数据字典不齐时，不开展采集或部署，也不把UCI办公室数据冒充大学教室验证。

核心路线不需要UCI输入。扩展路线需要UCI来源文件，或使用--profile extended --download-external明确允许从官方源下载。详细安装与隔离重建见05、文档依赖/文档/reproduction.md。

## 使用步骤

填写历史日期、开始时间、时长与人数，查看课表空档候选，再选择一间并保存演示核查单。无结果时可采用同一天稍晚的时段建议，人数与时长保持原值。基础查询只依赖两份清洗后的数据文件，不要求模型文件齐备；数据缺失时必须先运行清洗重建。

研究结果默认收起，侧栏可开启并选择默认或统一研究模式。预测解释的是已排课记录，不能作为候选空档无人或允许进入的证据。核查单不是预约凭证；真实使用前还需确认最新课表、预约、管理权限与现场情况。

## 自动检查与限制

core重建执行主实验、查询检查和单元测试；四语交互检查可运行04、运行验证/测试/test_app.py。extended额外包括UCI、v5至v11分类器与阈值探索、unified分场景研究方案和risk_review四周配对风险复核，计算耗时更长。研究模式由侧栏显式选择，当前默认方案保留。风险报告中的假设误报成本不代表实测业务损失，不自动授权替换模型。

六份配套说明随包提供，包括测试需要读取的README、evaluation_protocol和data_card。安装命令把环境、下载缓存和临时文件放到D盘；解压目录也请放到D盘。完整extended构建后，可运行04、运行验证/代码/verify_release.py，检查实际生成的源码ZIP是否能在D盘另一全新目录从现有原始输入重建，并执行四语交互。该检查沿用当前Python环境，不下载或安装依赖，不等于新机器或第三方复现。验证结果按ZIP哈希绑定；重新打包或修改源码后需要重新核验。

低利用率是观测峰值人数/座位数小于10%，不等于无人。零峰值是另一个代理标签。不得将任一信号用于自动取消预约。LORO空间实验使用其他教室的多个时间段，不代表新校园未来效果。源码包通过打包完整性检查也不等于GitHub发布或第三方复现已完成。

本包为待发布源码候选，不授予尚未确认的源码或数据再分发许可。发布前须明确仓库地址及相应许可。
