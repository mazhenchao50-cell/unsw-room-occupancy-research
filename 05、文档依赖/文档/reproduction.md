# 安装与完整重建

所有命令在项目实施或源码包解压根目录执行。Python 3.13、Windows x64锁定依赖见同级依赖目录。新环境、下载、缓存、临时文件放在项目目录之外的同级工作目录（下例为上一级的UNSW_Reproduction）；本机现有环境与验证存档统一在毕业设计文件夹的“11、运行环境与验证存档（原D盘）”。工作目录位置不是算法要求。

## 新环境：安装和执行始终使用同一个解释器

```powershell
$taskRoot=Join-Path (Split-Path -Parent $PWD) 'UNSW_Reproduction'
$env:TEMP="$taskRoot\tmp"
$env:TMP=$env:TEMP
$env:PIP_CACHE_DIR="$taskRoot\cache"
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:UNSW_DOWNLOAD_DIR="$taskRoot\downloads"
$env:UNSW_CALENDAR_DIR=$env:UNSW_DOWNLOAD_DIR
New-Item -ItemType Directory -Force -Path $env:TEMP,$env:PIP_CACHE_DIR,$env:UNSW_DOWNLOAD_DIR | Out-Null
python -m venv "$taskRoot\.venv"
$python="$taskRoot\.venv\Scripts\python.exe"
& $python -m pip install --disable-pip-version-check -r '05、文档依赖/依赖/requirements-windows-py313.lock'
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
& $python -m pip check
```

上段中的基础python需为已安装Python 3.13。后续不覆盖$python，也不切回开发者旧环境。网络下载失败应保留安装日志，不能伪报环境通过。

## 输入与联网步骤

从[UNSW官方数据页](https://smartcampus.unsw.edu.au/roomoccupancy/index.html)取得[data.zip](https://smartcampus.unsw.edu.au/roomoccupancy/data.zip)，下载到上面的downloads目录。2026-11-11逐字节核验版本：23,603,263字节，SHA256 `0f5215b586c6d700fc4c7146d5326a562a0008541789f0fb6025b711a2bad273`。14份完整CSV包括2017/2018 attendance和week1–12 computed。

将这14份CSV复制到`01、数据处理/原始数据/UNSW/`。源码包data_requirements.json给出逐文件哈希；不能换成相似数据。首次下载日期未知，2026-11-11是再次验证日期。UNSW明确再分发许可尚未取得，源码包不携带原始数据。

完整研究路线还需要UCI原件及两份官方日历PDF。以下命令联网下载到显式目录，校验日历哈希，并将UCI研究输入复制进项目的数据目录：

```powershell
& $python '04、运行验证/代码/acquire_supporting.py' --download-dir $env:UNSW_DOWNLOAD_DIR
if ($LASTEXITCODE -ne 0) { throw '补充来源获取或校验失败' }
```

UCI是独立办公室诊断，不计入前三项UNSW指标。其CC BY 4.0来源页和下载哈希随原件保存；该许可不套用到UNSW。已有授权输入可直接复用，无需重复下载。

## 执行

```powershell
# 全部保留实验、补充研究、完整测试ID清单和四语交互
& $python '04、运行验证/代码/run_all.py' --profile extended
if ($LASTEXITCODE -ne 0) { throw '完整检查失败，先处理首个失败阶段' }
# 实际源码ZIP在独立目录从零重建
& $python '04、运行验证/代码/verify_release.py' --profile extended --output-root "$taskRoot\release_validation"
if ($LASTEXITCODE -ne 0) { throw '发布包重建失败' }
& $python -m streamlit run '03、系统应用/代码/app.py' --client.toolbarMode minimal
```

日常正式模型训练可单独运行`run_all.py --formal-only`：只重建数据、正式模型及数值推理核验，不耦合所有历史算法实验，也不记为完整检查。完整extended保留全部实验入口，包括v3至v11历史实验和补充研究01至23（15–19为2026-11-24复核实验：惯性基线、2018外部验证、报名泄漏敏感性、正式模型SHAP、无课时段空教室；20严格前推留一教室，21延续在室人数（在19目录内），22同等信息对比（在16目录内），23两段式概率校准）。

每次运行的阶段命令、退出码和日志在`04、运行验证/日志/rebuild_*/execution.json`。测试报告绑定全部测试方法ID、实际执行ID、测试源文件哈希；只跑一项或跳过不能拿到完整通过。实际ZIP验证绑定全部当前代码、数据要求和完整测试清单。

verify_release本身使用调用者解释器：只有确实按上面的新环境安装并运行，才能称为本地清洁环境复现。它不是独立第三方验收。公开GitHub版本须另核对提交与当前源码包，不把旧仓库提交当成新版已发布。

