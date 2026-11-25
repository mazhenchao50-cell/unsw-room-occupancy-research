# 来源与论断记录

2026-11-20当前结论：[原作者2019论文](https://www2.ee.unsw.edu.au/~vijay/pubs/jrnl/19IoTJ.pdf#page=7)第7页V-A定义enrollment为选修课程的学生人数，并作为预测输入；同页V节讨论课前数周的教室安排。第6页IV-A说明课堂attendance按课堂期间占用峰值形成。[2018数据演示说明](https://www2.ee.unsw.edu.au/~hhabibi/pubs/conf/18ipsn_demo.pdf)区分报名、出席和容量；[学校词汇表](https://my.unsw.edu.au/help/STA/courseClassGlossary.html)解释Enrolments为当前选课人数。这些依据支持限定UNSW历史研究使用报名字段，尚不能核实公开CSV逐值取得时间或解释双表差异。正式可发布证据摘要及原文哈希见`05、文档依赖/依赖/unsw_field_evidence.json`。不把时间元数据缺失写成已发生泄漏；下面按日期保留的读取失败不代表当前官方入口不可用。

2026-11-11 补充：从 [UNSW Smart Campus 首页](https://smartcampus.unsw.edu.au/) 的 View Data 找到 [当前官方数据目录](https://smartcampus.unsw.edu.au/roomoccupancy/index.html)。实际下载其中的 `data.zip`，通过压缩完整性检查，两个考勤文件与十二个周文件均与本地版本字节一致。此结果补齐当前取得入口与输入身份核验。原论文的旧链接读取记录保留。官方索引列出数据包，作者的 [2018 数据说明](https://www2.ee.unsw.edu.au/~hhabibi/pubs/conf/18ipsn_demo.pdf) 记录研究数据曾公开提供下载，当前未找到明确再分发许可。逐文件证据在 `04、运行验证/日志/unsw_source_20261111/官方来源核对.json`，操作见 [安装、运行与隔离复现](reproduction.md)。

2026-10-31补充：UCI [Occupancy Detection官方页](https://archive.ics.uci.edu/dataset/357/occupancy+detection)，提供者Luis Candanedo，2016年，DOI 10.24432/C5X01N；官网记载占用真值来自每分钟带时间戳照片，许可CC BY 4.0。官方ZIP及网页已保存在 `01、数据处理/原始数据/UCI/`，哈希与时间依据见manifest.json。用于独立即时占用检测，不能证明本校部署、未来预测或UNSW模型迁移。该许可不适用于UNSW原始数据。

2026-10-31重新访问UNSW历史数据页，当前网页工具仍未读取成功；此事实不能证明页面永久失效，也没有补齐原下载日期或明确许可证。

以下为2026-10-14历史查阅记录。只保留支持具体论断的来源，不声称重建旧稿历史被引数量。

|来源|定位与用途|本轮状态|
|---|---|---|
|https://www2.ee.unsw.edu.au/~vijay/pubs/jrnl/19IoTJ.pdf|摘要及第V节：MLR/RF/SVR、出勤预测标签；第VI节：分配优化|作者原文可读取；项目标签与该研究不直接可比|
|https://www2.ee.unsw.edu.au/~vijay/pubs/conf/18ipsn.pdf|空间利用及配置优化，潜在节省仅作研究背景|作者原文可读取；非本项目实测收益|
|https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVR.html|SVR回归方法及参数|官方文档可读取|
|https://scikit-learn.org/stable/modules/preprocessing.html|预处理与标准化|官方文档可读取|
|https://smartcampus.unsw.edu.au/roomoccupancy/data/|论文数据发布页面|本轮工具读取失败，不能判定永久失效|

原始14个本地CSV的文件大小及SHA256见01、数据处理/清洗产物/input_manifest.json。原下载日期、发布版校验值与明确许可证未获得，不作补填。删除无官方凭据的NUS Vacansee论断，不保留无API快照的精确引用量。
