# 安装、运行与隔离复现

所有命令在项目实施目录执行。原始UNSW数据默认位于 `01、数据处理/原始数据/UNSW/`。现有 `.venv-repro` 是本机环境，复制源码后应重新安装依赖，不能直接复制虚拟环境代替安装。

## 首次安装

本轮使用Windows x64和Python 3.13.17；这是本轮完整四语回归使用的版本。原项目`.venv-repro`在本机不能可靠启动，不要将其验证状态当成通过。本机新建的隔离环境位于`D:\ProjectTools\UNSW_RoomReplay_Python313\.venv`，依赖锁文件安装后`pip check`通过；该环境使用电脑原有的Python 3.13.17基础运行时，不能单独复制到其他电脑。

在本机重跑时使用已验证环境：

```powershell
$envRoot = 'D:\ProjectTools\UNSW_RoomReplay_Python313'
$env:TEMP = Join-Path $envRoot 'Temp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $envRoot 'pip-cache'
$python = Join-Path $envRoot '.venv\Scripts\python.exe'
& $python -m pip check
& $python "04、运行验证\代码\verify_reproduction.py" --profile extended
```

首次在其他Windows电脑建环境时，先确认Python 3.13可用；将虚拟环境、`TEMP`、`TMP`和`PIP_CACHE_DIR`指定到D盘后，再按锁文件安装依赖。安装器可能单独建立系统包缓存，下载到D盘并不保证安装器的缓存也在D盘，完成后需核对缓存位置。本机此次测试中发现的C盘安装缓存副本已删除。

```powershell
python -m venv .venv-repro
.venv-repro\Scripts\python.exe -m pip install -r "05、文档依赖\依赖\requirements-windows-py313.lock"
.venv-repro\Scripts\python.exe -m pip check
```

`requirements.txt`固定主依赖，但允许间接依赖变化；`requirements-windows-py313.lock`记录本轮安装的完整版本，不是对其他平台的兼容保证。原`requirements-lock.txt`保留作历史版本记录。新建环境时不要使用`--system-site-packages`。

## 重建和启动

```powershell
# 在本目录生成核心产物
.venv-repro\Scripts\python.exe "04、运行验证\代码\run_all.py" --profile core
# 核心重建成功后启动四语界面
.venv-repro\Scripts\python.exe -m streamlit run "03、系统应用\代码\app.py"
```

核心路线不需要UCI或v5旧产物。扩展路线使用`--profile extended`，缺少UCI来源文件时需显式增加`--download-external`。

扩展路线也执行 `02、模型实验/代码/models/forward_cold_benchmark.py`：在四个测试周分别留出一间教室，所有训练、选型和提示校准只读取其他教室的更早数据。结果位于 `02、模型实验/生成产物/forward_cold_benchmark/`。它是回顾研究的强基线对照，保留全部模型与未满足校准条件的折，不替换默认模型或正式验收条件。

## 查看一节课的预测依据

应用启动后，保留默认历史查询或自行选择日期与时段。在侧栏开启研究详情，找到“查看某节课的预测依据”，选择当前时段的一节课程。界面显示实际模型输入、每项因素的贡献百分点，以及模型基准、贡献合计和预测值。中英韩日界面均支持。统一研究模式中，当前解释覆盖已见教室的占用率回归分支。

## 从官方来源准备 UNSW 输入

从 [UNSW 智慧校园官方目录](https://smartcampus.unsw.edu.au/roomoccupancy/index.html) 下载 `data.zip`。2026-11-11 已实际下载并逐文件核对，包内 14 份 CSV 与本项目实验输入的 SHA256 全部一致。将两个学期的 attendance 文件和 week1 至 week12 的 computed 文件取出，放在 `01、数据处理/原始数据/UNSW/`，CSV 与该目录直接相邻。已有同名文件时，先核对哈希再决定是否替换。

源码包根目录的 `data_requirements.json` 提供 14 个文件各自的 SHA256。在解压后的源码包根目录运行以下命令，校验成功后执行核心重建。

```powershell
$requirements = Get-Content -Raw -Encoding UTF8 'data_requirements.json' | ConvertFrom-Json
if (@($requirements).Count -ne 14) { throw 'UNSW input list must contain 14 files' }
foreach ($entry in $requirements) {
    $inputPath = Join-Path '01、数据处理/原始数据/UNSW' $entry.file
    $actual = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256 -ErrorAction Stop).Hash
    if ($actual -ne $entry.sha256) { throw "Input hash mismatch: $inputPath" }
}
'Verified: 14 UNSW inputs'
```

本次实测的 ZIP 大小为 23,603,263 字节，SHA256 为 `0f5215b586c6d700fc4c7146d5326a562a0008541789f0fb6025b711a2bad273`。如果官方更新了打包方式，优先以 14 个 CSV 的内容哈希核对。研究者从官方来源自行取得数据，公开源码包只提供链接和哈希。现有来源未查到明确再分发许可。

## 不覆盖现有结果的验证

```powershell
.venv-repro\Scripts\python.exe "04、运行验证\代码\verify_reproduction.py" --profile extended
```

该命令将源码、维护文档和扩展路线所需的UCI原始来源复制到新的 `04、运行验证/日志/reproduction_*/project`，不复制处理后数据或模型。随后依次运行依赖一致性检查、全量重建和四语界面检查。每次验证保留独立目录、源码哈希和退出码。

它使用调用它的Python环境，不自动创建环境或安装依赖。因此“新环境安装”须有前面的安装记录，不能仅凭此命令成功就宣称重新安装完成。`verification.json`中的各阶段状态是复核入口，`run_all`的内部阶段日志位于副本的 `04、运行验证/日志/rebuild_*`。

## 失败时如何处理

优先读取第一处失败的阶段日志：缺少输入则修复路径或补源文件；依赖问题先运行`pip check`；权限或本地套接字受限则在允许该操作的环境复核。不要删除原始数据、调整标签、隐藏异常或直接跳到后续阶段。

复现通过只能证明指定环境与数据下的可执行性，不能证明零峰值现场真值、跨校园泛化、预约完整性或现场开放许可。
