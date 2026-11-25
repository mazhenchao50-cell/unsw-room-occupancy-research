"""Offline UI catalog; each row contains zh, en, ko, ja translations."""
LANGUAGES={'zh':'中文','en':'English','ko':'한국어','ja':'日本語'}
TEXT={
 'review_title':('历史课程复核清单','Historical class review queue','과거 수업 검토 목록','過去授業の確認リスト'),
 'review_scope':('按模型提示优先复核当天课程。目标是整节课观测峰值低于座位数10%，不是所选分钟内无人；开放时间、预约和进入权限均未核实。没有提示也不能排除漏报。','Prioritize historical classes for review. The target is whole-class observed peak below 10% of capacity, not vacancy during the selected minutes. Opening hours, bookings and access are unverified. No alert does not rule out a miss.','모델 표시 순으로 과거 수업을 검토합니다. 목표는 수업 전체 관측 최대 인원이 정원의 10% 미만인지이며, 선택 시간의 공실 여부가 아닙니다. 운영 시간·예약·출입은 미확인이고 알림이 없어도 미탐이 가능합니다.','モデルの表示を使って過去授業を確認します。対象は授業全体の観測最大人数が定員の10%未満かどうかで、選択時間の無人判定ではありません。開館時間・予約・入室許可は未確認で、警告がなくても見逃しはあり得ます。'),
 'review_select':('选择课次查看提示依据','Select a class to inspect its signals','근거를 볼 수업 선택','確認根拠を見る授業を選択'),
 'review_evidence':('两个模型的分数与这门课此前三次的记录，只作复核参考，不是确切概率，也不说明原因。','Scores from the two models and this course’s previous three classes are review aids only, not exact probabilities or causes.','두 모델의 점수와 이 과목의 이전 3회 기록은 검토 참고용이며 정확한 확률이나 원인이 아닙니다.','2つのモデルのスコアとこの科目の直近3回の記録は確認の参考であり、正確な確率や原因ではありません。'),
 'logistic_score':('逻辑回归分数','Logistic score','로지스틱 점수','ロジスティックスコア'),
 'tree_score':('浅层树分数','Shallow-tree score','얕은 트리 점수','浅い木のスコア'),
 'ensemble_score':('平均分数','Mean score','평균 점수','平均スコア'),
 'course_recent_mean3':('此前三次平均利用率','Previous-three mean utilization','이전 3회 평균 이용률','直近3回の平均利用率'),
 'course_recent_low3':('此前三次低利用率比例','Previous-three low-use fraction','이전 3회 저이용 비율','直近3回の低利用割合'),
 'course_seen':('有此前课程记录','Prior course observations exist','이전 수업 기록 있음','過去の授業記録あり'),
 'review_action':('人工复核记录','Manual review annotation','수동 검토 기록','手動確認の記録'),
 'review_pending':('待复核','Pending review','검토 대기','確認待ち'),
 'review_checked':('已对照历史标签','Historical label inspected','과거 라벨 확인','過去ラベル確認済み'),
 'review_false':('怀疑为误报，待调查','Suspected false alert; investigate','오탐 의심·조사 필요','誤検出の疑い・要調査'),
 'review_note':('复核依据或备注','Evidence or notes','근거 또는 메모','根拠またはメモ'),
 'review_download':('导出本次复核记录','Export this review','검토 기록 내보내기','確認記録を出力'),
 'history_rule_scope':('空教室候选来自历史时段规则：所选时段在已知课表中无课（含开课前15分钟），且该教室在更早几周的同一星期、同一时段被自发占用（≥5人）的比例低于50%。历史回放中，此规则推荐的时段约84%实际空闲（峰值不足5人）；若计入上一节课下课后留下的人，约57%。仅适用于工作日8:00–20:00；公开记录不能证明全天课表完整，开放权限与现场情况均未核实。','Candidates come from the historical slot rule: the selected hours have no known class (including 15 minutes before each class), and in earlier weeks this room was used informally (5 or more people) in under half of the same weekday-hour slots. In historical replay, about 84% of hours recommended by this rule were actually free (peak under 5 people); about 57% if people staying on after a class are counted. Weekdays 08:00–20:00 only. Public records do not prove complete daily timetables; access and on-site conditions are unverified.','후보는 과거 시간대 규칙에 따릅니다. 선택한 시간에 알려진 수업이 없고(수업 시작 15분 전 포함), 이전 주의 같은 요일·같은 시간대에 이 강의실이 자발적으로 사용된(5명 이상) 비율이 50% 미만입니다. 과거 재생에서 이 규칙이 추천한 시간의 약 84%가 실제로 비어 있었고(최대 5명 미만), 수업 후 남은 인원을 포함하면 약 57%입니다. 평일 08:00–20:00에만 적용됩니다. 공개 기록으로 일일 시간표의 완전성을 확인할 수 없으며 이용 허가와 현장 상황은 미확인입니다.','候補は過去の時間帯ルールによります。選択した時間に既知の授業がなく（授業開始15分前を含む）、以前の週の同じ曜日・同じ時間帯にこの教室が自発的に使われた（5人以上）割合が50%未満です。履歴再生では、このルールが推薦した時間の約84%が実際に空いていました（最大5人未満）。授業後に残った人を含めると約57%です。平日8:00–20:00のみ対象です。公開記録から一日の時間割の完全性は確認できず、使用許可と現地の状況は未確認です。'),
 'optional_invalid':('此补充报告缺失或格式错误，已停用该部分。','This optional report is missing or invalid; its panel is disabled.','보조 보고서가 없거나 잘못되어 해당 부분을 비활성화했습니다.','補足レポートが未作成または不正なため、その表示を無効にしました。'),
 'standard_missing':('正式方案尚不可用，请重建正式模型。旧基线需要单独选择。','The standard model is unavailable. Rebuild it; the baseline requires explicit selection.','정식 모델을 다시 생성하세요. 기존 모델은 직접 선택해야 합니다.','標準モデルを再構築してください。ベースラインは明示的な選択が必要です。'),
 'needs_title':('1 · 填写使用需求','1 · Set your requirements','1 · 이용 조건 입력','1 · 利用条件を入力'),
 'query_summary':('{date} · {start}–{end} · 需要{seats}个座位','{date} · {start}–{end} · {seats} seats needed','{date} · {start}–{end} · 필요 좌석 {seats}석','{date} · {start}–{end} · 必要座席数 {seats}席'),
 'result_counts':('符合座位要求：{eligible}间；其中空教室候选{gaps}间、此前同时段常被自发占用{used}间、有课冲突{conflicts}间、超出规则范围或信息不足{unknown}间。最多展示5间候选。','{eligible} rooms meet the seat requirement: {gaps} candidates, {used} often used informally at this time in earlier weeks, {conflicts} schedule conflicts, {unknown} outside the rule scope or with insufficient records. Up to 5 candidates are shown.','좌석 조건 충족 {eligible}개: 후보 {gaps}개, 이전 주 같은 시간대에 자주 자발적으로 사용된 강의실 {used}개, 수업 충돌 {conflicts}개, 규칙 범위 밖 또는 정보 부족 {unknown}개입니다. 후보는 최대 5개 표시합니다.','座席条件を満たす教室は{eligible}室：候補{gaps}室、以前の週の同じ時間帯によく自発的に使われた教室{used}室、授業との重複{conflicts}室、ルールの範囲外または情報不足{unknown}室。候補を最大5室表示します。'),
 'filter_details':('查看列出或排除教室的原因','Why rooms were included or excluded','강의실 포함·제외 이유 보기','教室が候補に含まれた理由や除外された理由'),
 'spare_seats':('多余座位','Spare seats','여유 좌석','余る座席数'),
 'select_candidate':('选择候选，查看核查事项','Select a candidate to see what to check','후보를 선택하여 확인 사항 보기','候補を選んで確認事項を見る'),
 'select_placeholder':('请选择一间候选教室','Choose a candidate room','후보 강의실을 선택하세요','候補の教室を選択してください'),
 'next_title':('3 · 下一步核查','3 · What to check next','3 · 다음 확인 사항','3 · 次に確認すること'),
 'selected_summary':('{room} · {seats}个座位 · 比需求多{spare}个座位','{room} · {seats} seats · {spare} more than requested','{room} · {seats}석 · 필요보다 {spare}석 많음','{room} · {seats}席 · 必要数より{spare}席多い'),
 'candidate_basis':('列出原因：在这批历史记录中，所选时段没有已知课表冲突，座位数满足需求。现场占用和开放权限均未核实。','Listed because these historical records show no known schedule conflict for the selected interval and enough seats. Actual occupancy and access permission are unverified.','이 과거 기록에서 선택 시간에 알려진 수업 충돌이 없고 좌석 수가 충분하여 표시했습니다. 실제 점유 및 이용 허가는 확인되지 않았습니다.','履歴上、指定時間に既知の授業との重複がなく、座席数を満たすため候補としています。現地の利用状況と使用許可は未確認です。'),
 'next_steps':('如果用于真实场景，请先核对最新课表与预约，再向管理方确认开放权限和现场使用情况。本演示不能替你预约、取消课程或批准进入。','For a real visit, check the latest timetable and bookings, then confirm access and current occupancy with the facility manager. This demo cannot book a room, cancel a class or grant access.','실제 방문 전 최신 시간표·예약을 확인하고 관리자에게 이용 허가와 현장 사용 상태를 확인하세요. 이 데모는 예약, 수업 취소 또는 출입 승인을 하지 않습니다.','実際に利用する際は最新の時間割と予約を調べ、管理者に使用許可と現地の利用状況を確認してください。このデモで予約、授業の取消、入室許可はできません。'),
 'brief_title':('教室候选演示核查单','Demo room-candidate checklist','강의실 후보 데모 확인서','教室候補のデモ確認メモ'),
 'brief_scope':('历史数据演示，仅供对照和核查；不是预约凭证或可用性确认。','Historical-data demo for comparison and review only; not a booking or availability confirmation.','과거 데이터 비교·확인용 데모이며 예약 증빙 또는 이용 가능 확인서가 아닙니다.','履歴データの比較・確認用デモです。予約証明や利用可能との確認ではありません。'),
 'save_brief':('保存演示核查单','Save demo checklist','데모 확인서 저장','デモ確認メモを保存'),
 'later_found':('当天稍晚可试 {time}：找到{count}间空教室候选。人数和时长保持不变；只检查随后4小时内每15分钟的开始时刻。','Try {time} on the same day: {count} candidates. Seats and duration stay unchanged. Search covers 15-minute start times within the next 4 hours.','같은 날 {time}에 후보 {count}개가 있습니다. 좌석 수와 이용 시간은 유지하며 이후 4시간의 15분 간격 시작 시각만 확인합니다.','同日の{time}なら候補が{count}室あります。座席数と利用時間は変えず、その後4時間内の15分刻みの開始時刻を調べます。'),
 'try_later':('改查 {time}','Search at {time}','{time}로 조회','{time}で再検索'),
 'no_later':('当天随后4小时内、按15分钟间隔检查的开始时刻也没有匹配候选。可调整日期或需求；这不代表已确认全部教室有人。','No match at the checked 15-minute start times within the next 4 hours of this date. Try another date or requirements; this does not confirm every room is occupied.','같은 날 이후 4시간의 15분 간격 시작 시각에서도 조건에 맞는 후보가 없습니다. 날짜나 조건을 바꿔 보세요. 모든 강의실이 사용 중임을 뜻하지 않습니다.','同日のその後4時間内、15分刻みで確認した開始時刻にも候補がありません。日付や条件を変更してください。すべての教室が使用中と確認されたわけではありません。'),
 'research_toggle':('显示预测与研究验证详情','Show predictions and research validation','예측 및 연구 검증 상세 보기','予測と研究検証の詳細を表示'),
 'research_separation':('以下预测只描述已排课会话，不参与空教室候选排序。切换模型不会取消已排课冲突。','Predictions below describe scheduled classes only and do not rank vacant-room candidates. Changing models never removes schedule conflicts.','아래 예측은 예정 수업에만 해당하며 빈 강의실 후보 순위에는 사용하지 않습니다. 모델을 바꿔도 수업 충돌은 해제되지 않습니다.','以下の予測は予定された授業のみが対象で、空き教室候補の順位には使いません。モデルを変えても授業との重複は解除されません。'),
 'research_unavailable':('课表查询仍可使用；预测详情暂不可用，请联系维护者检查研究产物。','Timetable search remains available. Prediction details are unavailable; ask the maintainer to check the research outputs.','시간표 조회는 계속 사용할 수 있습니다. 예측 상세는 준비되지 않았으므로 관리자에게 연구 결과 파일 확인을 요청하세요.','時間割検索は引き続き利用できます。予測の詳細は表示できないため、管理者に研究結果ファイルの確認を依頼してください。'),
 'prediction_mode':('预测方案','Prediction mode','예측 방식','予測方式'),
 'system_current':('原始基线方案','Original baseline','기존 기준 모델','元のベースライン'),
 'system_unified':('正式分场景方案','Standard routed model','정식 상황별 모델','標準の状況別モデル'),
 'unified_title':('有课会话占用与低利用率预测','Scheduled occupancy and low-utilization predictions','수업 점유율 및 저이용 예측','授業の利用率と低利用の予測'),
 'unified_scope':('正式研究方案（unified_v6）：已见教室的占用率由两段式模型给出（先估计低利用可能性，再预测正常开课时的占用率）；低利用提示由原分类器（逻辑回归与浅层LightGBM等权平均，阈值0.50）、情境模型多数决补充和公共假日日历三者合成；未见教室使用含教学周的冷启动模型（cold_week）。下表从实际预测结果计算；低利用率不等于无人或可以释放教室。','Formal research model (unified_v6): known-room occupancy comes from a two-part model (low-use likelihood first, then occupancy if the class is held). Low-use alerts combine the original classifier (equal-weight logistic regression and shallow LightGBM, threshold 0.50), a contextual majority vote and the public-holiday calendar. Unseen rooms use the cold-start model with teaching week (cold_week). Metrics below come from actual predictions; low use does not establish vacancy or room release.','정식 연구 모델(unified_v6): 기존 강의실 점유율은 2단계 모델(저이용 가능성 추정 후 정상 개강 시 점유율 예측)로 계산합니다. 저이용 알림은 기존 분류기(로지스틱 회귀와 얕은 LightGBM 동일 가중 평균, 임계값 0.50), 상황 모델 다수결 보완, 공휴일 달력을 합친 것입니다. 새 강의실은 교육 주차를 포함한 콜드 스타트 모델(cold_week)을 사용합니다. 아래 지표는 실제 예측에서 계산하며 저이용은 공실이나 해제 가능을 뜻하지 않습니다.','正式研究モデル（unified_v6）：既知教室の利用率は二段階モデル（低利用の可能性を推定し、次に通常実施時の利用率を予測）で求めます。低利用警告は元の分類器（ロジスティック回帰と浅いLightGBMの等重み平均、閾値0.50）、状況モデルの多数決補足、祝日カレンダーを合わせたものです。未知教室は教育週を含むコールドスタートモデル（cold_week）を使います。以下は実際の予測から算出した値で、低利用は空室や解放可能を意味しません。'),
 'unified_cutoff':('仅预测训练和校准截止日 {date} 之后的会话。','Predictions are restricted to sessions after fitting and calibration cutoff {date}.','학습 및 보정 마감일 {date} 이후 수업만 예측합니다.','学習・較正の最終日 {date} より後の授業のみ予測します。'),
 'unified_risk':('第{week}周低利用率提示：命中{tp}、误报{fp}、漏报{fn}；精确率{precision}，召回率{recall}。','Week {week} low-use alerts: {tp} matches, {fp} false alerts, {fn} misses; precision {precision}, recall {recall}.','{week}주차 저이용 알림: 적중 {tp}, 오탐 {fp}, 미탐 {fn}; 정밀도 {precision}, 재현율 {recall}.','第{week}週の低利用警告：一致{tp}、誤検出{fp}、見逃し{fn}。適合率{precision}、再現率{recall}。'),
 'unified_unavailable':('研究方案的模型、数据或源码与验证记录不一致，请重建后再使用。','Research model, data or source differs from its verified record. Rebuild before use.','연구 모델, 데이터 또는 코드가 검증 기록과 다릅니다. 다시 생성한 후 사용하세요.','研究モデル、データまたはコードが検証記録と一致しません。再構築してから使用してください。'),
 'unified_explain':('正式模型为两段式：显示的占用率=未开课概率×低利用率平均值+(1−该概率)×正常开课时的占用率预测。下表解释后一部分（已见教室、正常开课条件下的LightGBM）；未开课概率见低利用率分类器解释，新教室静态模型不在此表。','The formal model is two-part: shown occupancy = probability of not being held × low-use mean + (1 − that probability) × occupancy predicted if held. The table explains the latter (known-room LightGBM conditional on the class being held); the not-held probability is explained by the low-use classifier, and the unseen-room static model is not covered.','정식 모델은 2단계입니다: 표시 점유율 = 미개강 확률 × 저이용 평균 + (1 − 해당 확률) × 정상 개강 시 점유율 예측. 아래 표는 후자(기존 강의실, 정상 개강 조건의 LightGBM)를 설명하며, 미개강 확률은 저이용 분류기 설명을 참조하고 새 강의실 정적 모델은 포함하지 않습니다.','正式モデルは二段階です：表示利用率＝未実施確率×低利用平均＋(1−その確率)×通常実施時の利用率予測。下表は後者（既知教室・通常実施条件のLightGBM）を説明します。未実施確率は低利用分類器の説明を参照し、未知教室の静的モデルは含みません。'),
 'route_label':('预测分工','Prediction branch','예측 분기','予測の分岐'),
 'route_known':('已见教室','Known room','기존 강의실','既知の教室'),
 'route_unseen':('未见教室','Unseen room','새 강의실','未知の教室'),
 'low_score':('低利用率模型得分','Low-use model score','저이용 모델 점수','低利用モデルスコア'),
 'low_alert':('低利用率提示','Low-use alert','저이용 알림','低利用警告'),
 'cold_start_experiment':('新教室预测研究进展','Unseen-room prediction study','새 강의실 예측 연구','未知の教室の予測研究'),
 'cold_start_scope':('此处是独立候选的历史留一教室验证，尚未替换现用模型。选参数时也按教室隔离；不能据此保证新校园或未来表现。','This is a separate candidate evaluated retrospectively with held-out rooms. It has not replaced the current model. Model selection also separates rooms; new-campus or future performance is not guaranteed.','별도 후보 모델의 과거 강의실 제외 검증 결과이며 현재 모델을 대체하지 않았습니다. 설정 선택에서도 강의실을 분리했습니다. 새 캠퍼스나 미래 성능을 보장하지 않습니다.','独立した候補の教室単位の履歴検証で、現行モデルは置き換えていません。設定の選択でも教室を分離しています。別キャンパスや将来の性能は保証しません。'),
 'cold_start_summary':('九间教室平均RMSE：{rmse}；同方案随机切分RMSE：{random}。数值过线仍需结合误差范围判断。','Mean RMSE across nine rooms: {rmse}; same-method random-split RMSE: {random}. Numeric thresholds must be interpreted with uncertainty.','9개 강의실 평균 RMSE: {rmse}, 같은 방법의 무작위 분할 RMSE: {random}. 수치 기준 충족 여부는 불확실성과 함께 해석해야 합니다.','9教室の平均RMSE：{rmse}、同じ方法のランダム分割RMSE：{random}。数値基準の達成は不確実性と併せて判断してください。'),
 'setup_required':('演示所需的数据或模型尚未准备完成，请联系维护者完成初始化后重试。','Required demo data or models are not ready. Ask the maintainer to finish setup and retry.','시연에 필요한 데이터 또는 모델이 준비되지 않았습니다. 관리자에게 초기 설정 완료를 요청한 후 다시 시도해 주세요.','デモに必要なデータまたはモデルが未準備です。管理者に初期設定を依頼してから再試行してください。'),
 'title':('校园课程利用率 · 历史复核','Campus class utilization · Historical review','캠퍼스 수업 이용률 · 과거 기록 검토','キャンパス授業利用率 · 履歴の確認'),
 'intro':('选择UNSW 2017年第8、10、11或12周日期，查看模型提示、课程历史及人工复核记录，并按历史时段规则查找空教室候选。支持四种语言；当前不提供实时预约。','Choose a date in UNSW 2017 weeks 8, 10, 11 or 12 to inspect model signals, course history and review annotations, and to find vacant-room candidates with the historical slot rule. Four languages are supported; live booking is unavailable.','UNSW 2017년 8·10·11·12주차 날짜를 선택하여 모델 신호, 수업 이력 및 검토 기록을 확인하고 과거 시간대 규칙으로 빈 강의실 후보를 찾으세요. 네 언어를 지원하며 실시간 예약은 제공하지 않습니다.','UNSWの2017年第8・10・11・12週の日付を選び、モデルの表示、授業履歴、確認記録を調べ、過去の時間帯ルールで空き教室の候補を探します。4言語に対応し、リアルタイム予約は提供していません。'),
 'date':('历史日期','Historical date','과거 날짜','履歴の日付'),
 'time_basis':('日期与时刻沿用UNSW原始数据的校园当地时间，未转换为你当前所在地时间。','Dates and times follow the original UNSW campus-local records; they are not converted to your current local time.','날짜와 시각은 UNSW 원본 데이터의 캠퍼스 현지 시간을 따르며 사용자 지역 시간으로 변환하지 않습니다.','日時はUNSW元データのキャンパス現地時刻で表示し、現在地の時刻には変換していません。'),
 'start':('开始时间','Start time','시작 시각','開始時刻'),
 'duration':('使用时长（分钟）','Duration (minutes)','사용 시간(분)','利用時間（分）'),
 'capacity':('所需座位','Seats needed','필요 좌석 수','必要な座席数'),
 'midnight':('使用时段不能跨越当天午夜，请提前开始时间或缩短使用时长。','The interval cannot cross midnight. Choose an earlier start or shorter duration.','사용 시간이 자정을 넘을 수 없습니다. 시작 시각을 앞당기거나 사용 시간을 줄여 주세요.','利用時間は日付をまたげません。開始時刻を早めるか利用時間を短くしてください。'),
 'query_error':('无法完成查询，请检查时间、时长和座位需求。','Unable to complete the query. Check the time, duration and seats.','조회할 수 없습니다. 시각, 사용 시간, 좌석 수를 확인해 주세요.','検索できません。時刻、利用時間、座席数を確認してください。'),
 'top':('2 · 查看空教室候选','2 · Review vacant-room candidates','2 · 빈 강의실 후보 확인','2 · 空き教室の候補を確認'),
 'ranking':('按满足需求后的座位数升序排列。候选均需现场核实占用与开放权限；有课时即使预测低利用率也不推荐。','Ranked by smallest sufficient capacity. Check actual occupancy and access permission. Scheduled rooms remain blocked even with low predicted utilization.','필요 좌석 수를 충족하는 작은 강의실부터 표시합니다. 실제 점유와 개방 여부를 확인해야 합니다. 예측 이용률이 낮아도 수업이 있는 강의실은 추천하지 않습니다.','必要座席数を満たす小さな教室から表示します。現地の利用状況と使用許可を確認してください。予測利用率が低くても授業のある教室は推薦しません。'),
 'empty':('当前条件下没有候选。可调整时间或座位需求；规则只覆盖工作日8:00–20:00。这不代表所有教室都已确认有人。','No candidates match. Try another time or capacity; the rule covers weekdays 08:00–20:00 only. This does not prove that every room is occupied.','조건에 맞는 후보가 없습니다. 시간이나 좌석 수를 조정해 보세요. 규칙은 평일 08:00–20:00에만 적용됩니다. 모든 강의실에 사람이 있다는 뜻은 아닙니다.','条件に合う候補がありません。時刻や座席数を変更してください。ルールは平日8:00–20:00のみ対象です。すべての教室に人がいると確認されたわけではありません。'),
 'filters':('筛选说明','Filtering details','필터링 설명','絞り込みの詳細'),
 'active_title':('有课会话预测及零峰值信号','Scheduled-class predictions and zero-peak signal','수업 예측 및 최대 관측 인원 0명 신호','授業予測と観測最大人数ゼロのシグナル'),
 'definitions':('低利用率标签：观测峰值人数/座位数 < 10%。No-show实验标签：传感器推导的会话峰值人数为0。风险提示不能用于取消预约。','Low-utilization label: observed peak attendance / seats < 10%. Experimental no-show label: sensor-derived session peak equals zero. Alerts do not authorize cancelling bookings.','저이용 라벨은 관측 최대 인원/좌석 수가 10% 미만입니다. 노쇼 실험 라벨은 센서로 추정한 수업 최대 인원이 0명인 경우입니다. 알림만으로 예약을 취소할 수 없습니다.','低利用ラベルは観測最大人数／座席数が10%未満です。ノーショー実験ラベルはセンサーから推定した授業最大人数が0人の場合です。警告だけで予約を取り消すことはできません。'),
 'label_scope':('零峰值标签尚未逐条现场核验。取消课程、课表变更或传感器问题均可能影响记录；无法仅凭此标签判断原因或确认爽约。','Zero-peak labels have not been individually verified. Cancellations, schedule changes or sensor issues may affect records; this label alone cannot establish the cause or confirm a no-show.','최대 인원 0명 라벨은 개별 현장 검증을 거치지 않았습니다. 수업 취소, 시간표 변경이나 센서 문제가 기록에 영향을 줄 수 있으며 라벨만으로 원인이나 노쇼를 확정할 수 없습니다.','最大人数0人のラベルは個別に現地確認されていません。授業の取消、時間割の変更、センサーの問題が記録に影響する可能性があり、このラベルだけでは原因や無断欠席を確定できません。'),
 'no_active':('所选时段没有可显示的有课会话预测。','No scheduled-class predictions are available for this interval.','선택한 시간대에 표시할 수업 예측이 없습니다.','指定時間帯に表示できる授業の予測はありません。'),
 'explain':('模型解释','Model explanation','모델 설명','モデルの説明'),
 'local_title':('查看某节课的预测依据','Explain a class prediction','수업별 예측 근거 보기','授業ごとの予測根拠'),
 'local_select':('选择当前时段的课程','Select a class in this interval','현재 시간대의 수업 선택','この時間帯の授業を選択'),
 'local_value':('模型实际输入值','Actual model input','모델 실제 입력값','モデルへの実際の入力値'),
 'local_pp':('占用率贡献（百分点）','Occupancy contribution (percentage points)','점유율 기여(퍼센트포인트)','利用率への寄与（ポイント）'),
 'local_summary':('模型基准 {base}，各因素合计贡献 {delta} 个百分点，原始预测 {raw}，界面显示 {prediction}。','Model baseline {base}, total contribution {delta} percentage points, raw prediction {raw}, displayed prediction {prediction}.','모델 기준값 {base}, 요인 기여 합계 {delta}퍼센트포인트, 원시 예측 {raw}, 표시 예측 {prediction}.','モデル基準値 {base}、要因の寄与合計 {delta}ポイント、元の予測 {raw}、表示値 {prediction}。'),
 'local_scope':('正值推高、负值拉低本节课的占用率预测，按贡献绝对值排序。基准为模型解释基准。界面将负预测归零，超过100%的预测保留以呈现超容量。此表解释占用率回归，低利用率或零峰值提示需另看其模型。','Positive values raise and negative values lower this class’s occupancy prediction, ordered by absolute contribution. The baseline is the model explanation baseline. Negative predictions are displayed as zero; predictions above 100% retain overcrowding information. This table explains occupancy regression; alerts use their own models.','양수는 이 수업의 예측 점유율을 높이고 음수는 낮춥니다. 절대 기여도순입니다. 기준값은 모델 설명 기준값입니다. 음수 예측은 0으로 표시하며 100% 초과 예측은 과밀 정보를 유지합니다. 이 표는 점유율 회귀를 설명하며 알림 모델은 별도입니다.','正の値はこの授業の予測利用率を上げ、負の値は下げます。絶対寄与度順です。基準値はモデルの説明基準値です。負の予測は0で表示し、100%を超える予測は過密情報として保持します。この表は利用率回帰を説明し、警告のモデルは別にあります。'),
 'local_unavailable':('当前记录缺少可核对的占用率回归解释，请联系维护者检查模型与课程记录。','A matching occupancy-regression explanation is unavailable. Ask the maintainer to check the model and class record.','현재 기록에 대응하는 점유율 회귀 설명을 확인할 수 없습니다. 관리자에게 모델과 수업 기록 확인을 요청하세요.','この記録に対応する利用率回帰の説明を確認できません。管理者にモデルと授業記録の確認を依頼してください。'),
 'shap_note':('SHAP反映模型关联，不是因果关系。主模型尚未在2018年、新校园或无课时段验证。','SHAP describes associations, not causation. The primary model is not validated for 2018, new campuses or unscheduled periods.','SHAP은 모델의 연관성이며 인과관계가 아닙니다. 주 모델은 2018년, 새 캠퍼스, 비수업 시간대에 대해 검증되지 않았습니다.','SHAPは関連性を示し、因果関係ではありません。主モデルは2018年、別のキャンパス、授業のない時間帯では未検証です。'),
 'room':('教室','Room','강의실','教室'), 'seats':('座位数','Seats','좌석 수','座席数'),
 'status':('课表状态','Timetable status','시간표 상태','時間割の状態'),
 'availability':('现场可用性','Verified availability','현장 사용 가능 여부','現地の利用可否確認'),
 'reason':('说明','Explanation','설명','説明'),
 'conflict':('课表冲突','Schedule conflict','수업 시간 충돌','授業と重複'),
 'unknown':('超出规则范围或课表信息不足','Outside rule scope or insufficient schedule data','규칙 범위 밖 또는 시간표 정보 부족','ルールの範囲外または時間割の情報不足'),
 'gap':('课表空档，现场待核实','Timetable gap; check on site','시간표상 빈 시간, 현장 확인 필요','時間割は空き、現地確認が必要'),
 'unverified':('未核实','Not verified','미확인','未確認'), 'verified':('已核实','Verified','확인됨','確認済み'),
 'conflict_reason':('课表冲突，不推荐','Scheduled conflict; not recommended','수업 시간 충돌로 추천하지 않음','授業と重複するため推薦対象外'),
 'unknown_reason':('超出历史规则范围（工作日8:00–20:00、与课程前后间隔足够）或课表信息不足，不能推断为空闲','Outside the historical rule scope (weekdays 08:00–20:00, clear of class windows) or insufficient schedule data; vacancy cannot be inferred','과거 규칙 범위(평일 08:00–20:00, 수업 시간과 겹치지 않음) 밖이거나 시간표 정보가 부족하여 공실 판단 불가','過去ルールの範囲外（平日8:00–20:00、授業時間と重ならない）または時間割情報が不足しており空室と判断できません'),
 'gap_reason':('仅为课表空档候选，现场占用及开放权限待核实','Timetable-gap candidate only; check occupancy and access permission','시간표상 빈 시간 후보이며 실제 점유와 사용 허가 확인 필요','時間割の空き時間候補です。利用状況と使用許可を確認してください'),
 'history_vacant':('历史时段规则候选，现场待核实','Historical slot-rule candidate; check on site','과거 시간대 규칙 후보, 현장 확인 필요','過去の時間帯ルールの候補、現地確認が必要'),
 'history_vacant_reason':('无已知课表冲突，此前同时段自发占用比例低于50%；现场占用及开放权限待核实','No known class; earlier same-slot informal use below 50%. Check occupancy and access permission','알려진 수업이 없고 이전 같은 시간대 자발적 사용 비율이 50% 미만입니다. 실제 점유와 사용 허가 확인 필요','既知の授業がなく、以前の同じ時間帯の自発的利用は50%未満です。利用状況と使用許可を確認してください'),
 'history_used':('此前同时段常被自发占用','Often used informally at this time','이전 같은 시간대에 자주 자발적 사용','以前の同じ時間帯によく自発的に利用'),
 'history_used_reason':('无课但此前同时段自发占用比例≥50%，不推荐','No class, but earlier same-slot informal use is 50% or more; not recommended','수업은 없지만 이전 같은 시간대 자발적 사용 비율이 50% 이상이므로 추천하지 않음','授業はないが以前の同じ時間帯の自発的利用が50%以上のため推薦対象外'),
 'history_rate':('此前同时段自发占用比例','Earlier same-slot informal-use share','이전 같은 시간대 자발적 사용 비율','以前の同じ時間帯の自発的利用割合'),
 'history_n':('此前同时段记录数','Earlier same-slot records','이전 같은 시간대 기록 수','以前の同じ時間帯の記録数'),
 'history_basis':('列出原因：所选时段在已知课表中无课（含开课前15分钟）；此前{n}次同一星期同一时段中，该教室被自发占用的比例为{rate}，低于50%。历史回放中此规则推荐的时段约84%实际空闲。现场占用和开放权限均未核实。','Listed because the known timetable has no class in the selected hours (including 15 minutes before classes), and in the previous {n} same weekday-hour slots this room was used informally {rate} of the time, below 50%. In historical replay about 84% of hours recommended by this rule were free. Actual occupancy and access permission are unverified.','선택 시간에 알려진 수업이 없고(수업 시작 15분 전 포함), 이전 {n}회의 같은 요일·같은 시간대에 이 강의실의 자발적 사용 비율이 {rate}로 50% 미만이라 표시했습니다. 과거 재생에서 이 규칙이 추천한 시간의 약 84%가 비어 있었습니다. 실제 점유와 이용 허가는 확인되지 않았습니다.','選択した時間に既知の授業がなく（授業開始15分前を含む）、以前{n}回の同じ曜日・同じ時間帯でこの教室が自発的に使われた割合は{rate}で50%未満のため候補としています。履歴再生ではこのルールが推薦した時間の約84%が空いていました。現地の利用状況と使用許可は未確認です。'),
 'history_basis_prior':('列出原因：所选时段在已知课表中无课（含开课前15分钟）；该教室此前没有同一星期同一时段的无课记录，按全部教室此前的自发占用比例{rate}判断，低于50%。依据较弱，现场占用和开放权限均未核实。','Listed because the known timetable has no class in the selected hours (including 15 minutes before classes). This room has no earlier unscheduled record for the same weekday and hour, so the all-room earlier informal-use share ({rate}, below 50%) is used. Weaker evidence; actual occupancy and access permission are unverified.','선택 시간에 알려진 수업이 없습니다(수업 시작 15분 전 포함). 이 강의실은 같은 요일·시간대의 이전 무수업 기록이 없어 전체 강의실의 이전 자발적 사용 비율({rate}, 50% 미만)을 사용했습니다. 근거가 약하며 실제 점유와 이용 허가는 확인되지 않았습니다.','選択した時間に既知の授業がありません（授業開始15分前を含む）。この教室には同じ曜日・時間帯の以前の授業なし記録がないため、全教室の以前の自発的利用割合（{rate}、50%未満）で判断しました。根拠は弱く、現地の利用状況と使用許可は未確認です。'),
 'course':('课程编号','Course ID','과목 ID','科目ID'),
 'course_start':('课程开始','Class start','수업 시작','授業開始'),
 'course_end':('课程结束','Class end','수업 종료','授業終了'),
 'prediction':('预测峰值占用率','Predicted peak occupancy','예측 최대 점유율','予測最大利用率'),
 'probability':('零峰值模型得分（未校准）','Zero-peak model score (uncalibrated)','최대 관측 인원 0명 모델 점수(미보정)','観測最大人数ゼロのモデルスコア（未較正）'),
 'alert':('零峰值提示','Zero-peak alert','최대 관측 인원 0명 알림','観測最大人数ゼロの警告'),
 'alert_yes':('已提示','Flagged','알림 표시','警告あり'),
 'alert_no':('未触发','Not triggered','알림 없음','警告なし'),
 'missing':('暂无预测','No prediction','예측 없음','予測なし'),
 'feature':('特征','Feature','특성','特徴量'),
 'mean_abs_shap':('平均绝对SHAP值','Mean absolute SHAP','평균 절대 SHAP 값','平均絶対SHAP値'),
 'share':('贡献占比','Contribution share','기여 비율','寄与率'),
 'spearman':('Spearman相关系数','Spearman correlation','Spearman 상관계수','Spearman相関係数'),
 'direction':('关联方向','Association direction','연관 방향','関連の方向'),
 'positive':('正相关','Positive association','양의 상관','正の関連'),
 'negative':('负相关','Negative association','음의 상관','負の関連'),
 'constant':('常量或无变化，无法计算','Constant or unchanged; undefined','상수 또는 변화 없음, 계산 불가','定数または変化なし、算出不可'),
 'course_hist_mean':('课程历史平均占用率','Historical course mean occupancy','과목 과거 평균 점유율','科目の過去平均利用率'),
 'course_hist_n':('课程历史样本数','Historical course sample count','과목 과거 표본 수','科目の履歴サンプル数'),
 'doors':('门数','Door count','출입문 수','出入口数'),
 'enrollments':('选课人数','Enrollment','수강 신청 인원','履修登録者数'),
 'weekday':('星期','Day of week','요일','曜日'),
 'duration_h':('课程时长（小时）','Class duration (hours)','수업 시간(시간)','授業時間（時間）'),
 'course_start_h':('课程开始时刻','Class start hour','수업 시작 시각','授業開始時刻'),
 'is_morning':('是否上午','Morning indicator','오전 여부','午前フラグ'),
 'is_weekend':('是否周末','Weekend indicator','주말 여부','週末フラグ'),
 'evidence':('真实数据与验证范围','Real data and validation scope','실제 데이터와 검증 범위','実測データと検証範囲'),
 'primary_data':('本系统已使用UNSW公开真实传感器与考勤记录，无需上传本校数据即可运行历史回放。','This replay already uses public real UNSW sensor and attendance records. No local-campus upload is needed.','이미 UNSW 공개 실측 센서 및 출석 기록을 사용합니다. 본교 데이터 업로드 없이 과거 데이터를 재생할 수 있습니다.','UNSWの公開実測センサー・出席記録を使用しています。自校データをアップロードせずに履歴再生できます。'),
 'external_data':('补充验证使用UCI办公室占用实测数据（CC BY 4.0）。这是单独训练的即时有人/无人检测，不是本校验证、主模型迁移或未来空教室预测。','The supplementary check uses real UCI office data (CC BY 4.0). A separate model detects current occupancy; this is not local-campus validation, primary-model transfer or future classroom prediction.','보조 검증은 UCI 사무실 실측 데이터(CC BY 4.0)로 별도 학습한 현재 재실 감지입니다. 본교 검증, 주 모델 전이, 미래 강의실 예측이 아닙니다.','補足検証はUCIのオフィス実測データ（CC BY 4.0）で別途学習した現在の在室検出です。自校の検証、主モデルの転移、将来の空室予測ではありません。'),
 'source':('数据来源','Data source','데이터 출처','データの出典'),
 'samples':('测试样本数','Test samples','테스트 표본 수','テスト件数'),
 'empty_precision':('无人检测精确率','Vacancy precision','공실 감지 정밀도','無人検出の適合率'),
 'empty_recall':('无人检测召回率','Vacancy recall','공실 감지 재현율','無人検出の再現率'),
 'empty_f1':('无人检测F1','Vacancy F1','공실 감지 F1','無人検出F1'),
 'false_empty':('有人却判为无人的记录数','Occupied records predicted empty','재실을 공실로 잘못 예측한 기록 수','在室を無人と誤判定した件数'),
 'no_external':('补充验证报告尚未生成。','Supplementary validation is not available yet.','보조 검증 보고서가 아직 없습니다.','補足検証レポートはまだありません。'),
 'risk_reliability':('零峰值信号仅供研究：第12周{alerts}次提示中，相对代理标签命中{true}次、误报{false}次，精确率{precision}。得分不是校准概率，也不证明爽约。','Research-only zero-peak signal: week 12 had {alerts} alerts, {true} matches and {false} false positives against the proxy label; precision {precision}. Scores are not calibrated probabilities or proof of a no-show.','연구용 최대 관측 인원 0명 신호입니다. 12주차 알림 {alerts}건 중 대리 라벨 기준 적중 {true}건, 오탐 {false}건, 정밀도 {precision}입니다. 점수는 보정 확률이나 실제 노쇼의 증거가 아닙니다.','研究用の観測最大人数ゼロのシグナルです。第12週の警告{alerts}件中、代理ラベルに対する一致は{true}件、誤検出は{false}件、適合率は{precision}です。スコアは較正確率や無断欠席の証拠ではありません。'),
 'noshow_comparison':('零峰值信号改进实验对照','Zero-peak signal experiment comparison','최대 관측 인원 0명 신호 실험 비교','観測最大人数ゼロのシグナル実験比較'),
 'comparison_note':('候选模型仅作离线对照，尚未替换现用模型。各周结果均展示；误报减少时也要检查漏报，不能仅凭总分判断可靠。','The candidate is an offline comparison and has not replaced the current model. Inspect every week, including misses as well as false alerts.','후보 모델은 오프라인 비교용이며 현재 모델을 대체하지 않았습니다. 각 주의 오탐과 미탐을 함께 확인하세요.','候補モデルはオフライン比較用で、現行モデルを置き換えていません。各週の誤検出と見逃しを併せて確認してください。'),
 'calendar_review':('公共假日复核提示','Public-holiday review','공휴일 검토','祝日の確認'),
 'weekly_metrics':('四周低利用率检查','Four-week low-use checks','4주 저이용 점검','4週間の低利用チェック'),
 'week':('学期周次','Semester week','학기 주차','学期の週'),
 'model':('模型','Model','모델','モデル'),
 'original_model':('原模型','Original model','기존 모델','元のモデル'),
 'candidate_model':('改进候选','Candidate model','개선 후보','改善候補'),
 'precision':('精确率','Precision','정밀도','適合率'),
 'recall':('召回率','Recall','재현율','再現率'),
 'fp':('误报数','False alerts','오탐 수','誤検出数'),
 'fn':('漏报数','Missed events','미탐 수','見逃し数'),
}
TEXT.update({
 'context_probability':('情境模型分数','Context model score','상황 모델 점수','状況モデルのスコア'),
 'context_alert':('情境模型复核提示','Context review flag','상황 모델 검토 알림','状況モデルの確認警告'),
 'public_holiday':('公共假日情境','Public-holiday context','공휴일 상황','祝日の状況'),
 'context_explain':('情境补充提示为什么出现','Why the contextual review appears','상황 기반 추가 알림의 이유','状況に基づく追加警告の理由'),
 'context_scope':('普通日的历史特征不聚合公共假日记录，训练及评估课次仍全部保留。三个分类器至少两个分数达到0.50时补充复核，原提示不撤回。逻辑回归和提升树列为对数几率贡献；随机森林列是实际决策路径的概率变化（百分点），不是SHAP。各自重构后取三个分数的中位数；此分数不是校准概率。','Ordinary-day history excludes public holidays; all training and evaluation sessions remain. At least two of three component scores reaching 0.50 add a review without withdrawing original alerts. Logistic and boosted-tree contributions use log-odds; forest values are probability-point changes along actual decision paths, not SHAP. Reconstruct each score and take their median; it is not a calibrated probability.','평일 이력 특성에서는 공휴일 관측을 제외하지만 학습·평가 수업은 모두 유지합니다. 세 분류기 중 두 점수가 0.50 이상이면 기존 알림을 유지하며 추가 검토합니다. 로지스틱·부스팅 기여는 로그 오즈이고, 랜덤 포리스트는 실제 경로의 확률 변화로 SHAP이 아닙니다. 세 점수의 중앙값은 보정 확률이 아닙니다.','通常日の履歴特徴では祝日を除きますが、学習・評価の授業は全件保持します。3分類器中2つのスコアが0.50以上なら元の警告を保持して確認を追加します。ロジスティックとブースティングの寄与は対数オッズ、森林は実際の経路での確率変化でSHAPではありません。3スコアの中央値は較正確率ではありません。'),
 'context_reconstruct':('逻辑回归 {logistic_score:.4f}；提升树 {tree_score:.4f}；随机森林 {forest_score:.4f}；中位数 {context_score:.4f}。基准分别为 {logistic_base:.4f}、{tree_base:.4f}、{forest_base:.4f}。','Logistic {logistic_score:.4f}; boosted tree {tree_score:.4f}; forest {forest_score:.4f}; median {context_score:.4f}. Baselines: {logistic_base:.4f}, {tree_base:.4f}, {forest_base:.4f}.','로지스틱 {logistic_score:.4f}; 부스팅 {tree_score:.4f}; 포리스트 {forest_score:.4f}; 중앙값 {context_score:.4f}. 기준값: {logistic_base:.4f}, {tree_base:.4f}, {forest_base:.4f}.','ロジスティック {logistic_score:.4f}、ブースティング {tree_score:.4f}、森林 {forest_score:.4f}、中央値 {context_score:.4f}。基準値は {logistic_base:.4f}、{tree_base:.4f}、{forest_base:.4f}。'),
 'forest_probability_points':('随机森林路径贡献（百分点）','Forest path contribution (points)','포리스트 경로 기여(퍼센트포인트)','森林の経路寄与（ポイント）'),
 'classifier_explain':('为什么提示这节课','Why this class is flagged','이 수업에 알림이 표시되는 이유','この授業に警告が出る理由'),
 'classifier_scope':('正值增加、负值减少对应分类器的低利用倾向。每列贡献与各自基准相加得到对数几率，再分别转换为分数，两个分数取平均。它们不是概率百分点，也不表示因果。公共假日是单独的复核规则，不放入特征贡献。完整依据随复核记录导出。','Positive contributions increase the component’s low-use tendency; negative contributions decrease it. Add each column to its own baseline, apply the sigmoid, then average the two scores. These are log-odds, not probability points or causal effects. The public-holiday review is a separate rule. Full evidence is included in the review export.','양수 기여는 해당 분류기의 저이용 경향을 높이고 음수는 낮춥니다. 각 열과 기준값을 합산한 뒤 시그모이드를 적용하고 두 점수를 평균합니다. 확률의 퍼센트포인트나 인과 효과가 아닙니다. 공휴일 검토는 별도 규칙이며 전체 근거를 내보낼 수 있습니다.','正の寄与は各分類器の低利用傾向を高め、負の寄与は下げます。各列をそれぞれの基準値に加え、シグモイド変換した二つのスコアを平均します。確率のポイントや因果効果ではありません。祝日確認は別の規則です。全根拠を確認記録とともに出力します。'),
 'classifier_reconstruct':('逻辑回归基准 {logistic_base:.4f}，转换后分数 {logistic:.4f}；树模型基准 {tree_base:.4f}，转换后分数 {tree:.4f}；平均分数 {score:.4f}；分类阈值 {threshold:.2f}。','Logistic baseline {logistic_base:.4f}, score {logistic:.4f}; tree baseline {tree_base:.4f}, score {tree:.4f}; mean score {score:.4f}; threshold {threshold:.2f}.','로지스틱 기준 {logistic_base:.4f}, 점수 {logistic:.4f}; 트리 기준 {tree_base:.4f}, 점수 {tree:.4f}; 평균 점수 {score:.4f}; 임계값 {threshold:.2f}.','ロジスティック基準 {logistic_base:.4f}、スコア {logistic:.4f}、木の基準 {tree_base:.4f}、スコア {tree:.4f}、平均 {score:.4f}、閾値 {threshold:.2f}。'),
 'logistic_log_odds':('逻辑回归贡献','Logistic contribution','로지스틱 기여','ロジスティック寄与'),
 'tree_log_odds':('树模型贡献','Tree contribution','트리 기여','木モデルの寄与'),
 'enrollment_pressure':('选课人数与容量之比','Enrollment / capacity','수강 인원 / 정원','登録人数／定員'),
 'enrollment_missing_or_zero':('选课人数缺失或为零','Enrollment missing or zero','수강 인원 누락 또는 0','登録人数の欠損またはゼロ'),
 'log_seats':('容量的自然对数','Log capacity','정원의 자연로그','定員の自然対数'),
 'attendance_factor_history':('此前课程到课比例均值','Earlier attendance factor mean','이전 출석 비율 평균','過去の出席係数平均'),
 'low_use_history':('此前低利用率课次比例','Earlier low-use fraction','과거 저이용 수업 비율','過去の低利用授業割合'),
 'course_last_rate':('上次课程占用率','Previous class occupancy','직전 수업 점유율','前回授業の利用率'),
 'course_recent_mean5':('此前五次课程平均占用率','Previous five classes mean occupancy','이전 5회 수업 평균 점유율','直近5回授業の平均利用率'),
 'course_recent_low5':('此前五次课程低利用比例','Previous five classes low-use fraction','이전 5회 수업 저이용 비율','直近5回授業の低利用割合'),
 'course_trend3':('近期三次均值与历史均值之差','Recent three mean minus historical mean','최근 3회 평균과 과거 평균의 차이','直近3回平均と過去平均の差'),
 'course_last_delta':('最近两次课程占用率之差','Difference between last two classes','최근 두 수업 점유율 차이','直近2回授業の利用率差'),
 'course_room_last':('本教室本课程上次占用率','Previous occupancy for this course and room','이 강의실 과목의 직전 점유율','同じ教室と科目の前回利用率'),
 'course_room_mean3':('本教室本课程此前三次均值','Previous three mean for this course and room','이 강의실 과목의 이전 3회 평균','同じ教室と科目の直近3回平均'),
 'course_room_low3':('本教室本课程此前三次低利用比例','Previous three low-use fraction for course and room','이 강의실 과목의 이전 3회 저이용 비율','同じ教室と科目の直近3回低利用割合'),
 'room_recent_low':('教室此前21天低利用比例','Room low-use fraction over previous 21 days','강의실 이전 21일 저이용 비율','教室の過去21日間の低利用割合'),
 'global_recent_low':('全部教室此前21天低利用比例','All-room low-use fraction over previous 21 days','전체 강의실 이전 21일 저이용 비율','全教室の過去21日間の低利用割合'),
 'course_history_log_n':('课程历史次数的对数','Log course history count','과목 과거 횟수의 로그','科目履歴件数の対数'),
 'room_history_log_n':('教室历史次数的对数','Log room history count','강의실 과거 횟수의 로그','教室履歴件数の対数'),
 'days_since_course':('距上次课程的天数','Days since previous class','직전 수업 이후 경과 일수','前回授業からの日数'),
 'course_room_seen':('本教室本课程是否有历史','Prior course and room observations','이 강의실 과목의 과거 관측 존재','同じ教室と科目の履歴の有無'),
})
# 2026-11-24 heuristic review fixes F1-F5: plain review flag, plain-language reasons, candidate layout.
TEXT.update({
 'review_flag':('需复核','Review needed','검토 필요','要確認'),
 'flag_yes':('⚠ 需复核（{reasons}）','⚠ Review ({reasons})','⚠ 검토 필요({reasons})','⚠ 要確認（{reasons}）'),
 'flag_no':('无提示','No alert','알림 없음','警告なし'),
 'flag_reason_model':('模型','model','모델','モデル'),
 'flag_reason_context':('情境补充','context','상황 보완','状況補足'),
 'flag_reason_holiday':('公共假日','public holiday','공휴일','祝日'),
 'all_scores':('查看全部模型分数（研究用）','All model scores (research)','전체 모델 점수 보기(연구용)','全モデルスコアを見る（研究用）'),
 'plain_flagged':('**结论：模型判断这节课很可能低利用**（两个模型平均分{score:.2f}，超过0.50的提示线）。主要依据：{reasons}。','**Conclusion: the model expects this class to be low-use** (mean score {score:.2f}, above the 0.50 alert line). Main reasons: {reasons}.','**결론: 모델은 이 수업을 저이용으로 판단했습니다**(두 모델 평균 점수 {score:.2f}, 알림 기준 0.50 초과). 주요 근거: {reasons}.','**結論：モデルはこの授業を低利用と判断しました**（2モデルの平均スコア{score:.2f}、警告ライン0.50を超過）。主な根拠：{reasons}。'),
 'plain_not_flagged':('**结论：原模型没有提示这节课**（平均分{score:.2f}，低于0.50的提示线）。主要原因：{reasons}。','**Conclusion: the original model does not flag this class** (mean score {score:.2f}, below the 0.50 alert line). Main reasons: {reasons}.','**결론: 기존 모델은 이 수업에 알림을 표시하지 않았습니다**(평균 점수 {score:.2f}, 기준 0.50 미만). 주요 이유: {reasons}.','**結論：元のモデルはこの授業に警告を出していません**（平均スコア{score:.2f}、警告ライン0.50未満）。主な理由：{reasons}。'),
 'plain_none':('没有可以直接说明的主要因素','no single readable factor stands out','쉽게 설명할 수 있는 주요 요인이 없음','分かりやすい主要因子はありません'),
 'plain_holiday':('当天是公共假日，另按日历规则提示复核。','This date is a public holiday, so the calendar rule also asks for review.','이 날은 공휴일이어서 달력 규칙으로도 검토가 표시됩니다.','この日は祝日のため、カレンダー規則でも確認対象です。'),
 'plain_context':('情境模型也给出了复核提示，见下方“情境补充提示为什么出现”。','The context model also flags this class; see the contextual explanation below.','상황 모델도 검토를 표시했습니다. 아래 상황 기반 설명을 확인하세요.','状況モデルも確認を求めています。下の状況に基づく説明を参照してください。'),
 'plain_scope':('这只是复核线索：低利用率表示整节课人数可能很少或没有实际上课，不代表现在教室没人，也不代表可以进入或使用。','This is only a review lead: low use means the whole class may have had very few people or did not run. It does not mean the room is empty now or may be used.','이는 검토 단서일 뿐입니다. 저이용은 수업 전체 인원이 매우 적었거나 실제로 열리지 않았을 수 있다는 뜻이며, 지금 강의실이 비어 있거나 사용할 수 있다는 뜻이 아닙니다.','これは確認の手がかりにすぎません。低利用は授業全体の人数が非常に少ないか実施されなかった可能性を示し、今教室が空いている、または使えるという意味ではありません。'),
 'technical_details':('技术细节（研究用）','Technical details (research)','기술 세부 정보(연구용)','技術的な詳細（研究用）'),
 'unit_points':('{v:+.0f}个百分点','{v:+.0f} pp','{v:+.0f}%p','{v:+.0f}ポイント'),
 'unit_days':('{v:.0f}天','{v:.0f} days','{v:.0f}일','{v:.0f}日'),
 'unit_hours':('{v:.1f}小时','{v:.1f} h','{v:.1f}시간','{v:.1f}時間'),
 'list_sep':('；','; ','; ','、'),
 'rule_expander':('候选是怎么选出来的','How candidates are selected','후보는 어떻게 선정되나요','候補の選び方'),
 'active_query':('当前查询：{summary}','Current search: {summary}','현재 조회: {summary}','現在の検索：{summary}'),
 'review_placeholder':('请选择一节课','Choose a class','수업을 선택하세요','授業を選択してください'),
 'weekday_0':('周一','Mon','월','月'),
 'weekday_1':('周二','Tue','화','火'),
 'weekday_2':('周三','Wed','수','水'),
 'weekday_3':('周四','Thu','목','木'),
 'weekday_4':('周五','Fri','금','金'),
 'weekday_5':('周六','Sat','토','土'),
 'weekday_6':('周日','Sun','일','日'),
 'date_label':('{date}（{weekday}·第{week}周）','{date} ({weekday}, week {week})','{date} ({weekday}·{week}주차)','{date}（{weekday}・第{week}週）'),
 'holiday_mark':('·公共假日','· public holiday','·공휴일','・祝日'),
 'conflict_detail_reason':('有课 {times}，不推荐；该教室到 {free} 才没有已知课程','Scheduled {times}; not recommended. No known class from {free}','수업 {times}이 있어 추천하지 않음. {free}부터 알려진 수업 없음','授業 {times}のため推薦対象外。{free}以降は既知の授業なし'),
 'review_download_text':('导出可读摘要（文本）','Export readable summary (text)','읽기용 요약 내보내기(텍스트)','読みやすい要約を出力（テキスト）'),
 'export_note':('JSON 文件用于存档和核验；文本摘要便于阅读和转交。两者都不是取消课程或释放教室的依据。','The JSON file is for records and verification; the text summary is for reading and sharing. Neither authorizes cancelling a class or releasing a room.','JSON 파일은 보관·검증용이고 텍스트 요약은 읽고 전달하기 위한 것입니다. 둘 다 수업 취소나 강의실 해제의 근거가 아닙니다.','JSONファイルは保存・検証用、テキスト要約は閲覧・共有用です。どちらも授業の取消や教室の解放の根拠にはなりません。'),
 'summary_title':('历史课程复核摘要','Historical class review summary','과거 수업 검토 요약','過去授業の確認要約'),
 'summary_class':('课程','Class','수업','授業'),
 'loading':('正在载入模型与历史数据，首次打开约需10秒……','Loading models and historical data (about 10 seconds the first time)…','모델과 과거 데이터를 불러오는 중입니다(처음에는 약 10초)…','モデルと履歴データを読み込み中です（初回は約10秒）…'),
 'yes_label':('是','Yes','예','はい'),
 'no_label':('否','No','아니요','いいえ'),
})
CATALOG={locale:{key:values[i] for key,values in TEXT.items()} for i,locale in enumerate(LANGUAGES)}

def t(locale,key):
    return CATALOG.get(locale,CATALOG['en'])[key]

def room_display(frame,locale):
    import pandas as pd
    f=frame.copy()
    statuses={'scheduled_conflict':'conflict','schedule_unknown':'unknown','timetable_gap_occupancy_unknown':'gap',
              'history_rule_candidate':'history_vacant','history_rule_likely_used':'history_used'}
    def reason(row):
        times=getattr(row,'conflict_times',None)
        if row.status=='scheduled_conflict' and isinstance(times,str) and times:   # heuristic review F8
            return t(locale,'conflict_detail_reason').format(times=times,free=row.free_from)
        return t(locale,statuses.get(row.status,'unknown')+'_reason')
    f['reason']=[reason(row) for row in f.itertuples()]
    f['status']=f.status.map(lambda s:t(locale,statuses.get(s,'unknown')))
    f['verified_available']=f.verified_available.map(lambda value:t(locale,'verified' if value==True else 'unverified'))
    if 'history_rate' in f:
        f['history_rate']=f.history_rate.map(lambda x:f'{x:.0%}' if pd.notna(x) else '—')
        f['history_n']=f.history_n.map(lambda x:str(int(x)) if pd.notna(x) else '—')
    f=f.drop(columns=[c for c in ('conflict_times','free_from') if c in f])
    names={'room':'room','seats':'seats','status':'status','verified_available':'availability','reason':'reason','history_rate':'history_rate','history_n':'history_n'}
    return f.rename(columns={key:t(locale,target) for key,target in names.items()})

def active_display(frame,locale):
    import pandas as pd
    labels={'room':'room','course_id':'course','course_start':'course_start','course_end':'course_end','prediction':'prediction','no_show_probability':'probability','no_show_alert':'alert'}
    f=frame[list(labels)].copy()
    for key in ['prediction','no_show_probability']:
        f[key]=f[key].map(lambda x:f'{x:.1%}' if pd.notna(x) else t(locale,'missing'))
    f['no_show_alert']=f.no_show_alert.map(lambda x:t(locale,'missing' if pd.isna(x) else 'alert_yes' if bool(x) else 'alert_no'))
    return f.rename(columns={key:t(locale,value) for key,value in labels.items()})

def routed_display(frame,locale):
    import pandas as pd
    labels={'room':'room','course_id':'course','course_start':'course_start','course_end':'course_end','prediction':'prediction',
            'prediction_route':'route_label','low_probability':'low_score','context_probability':'context_probability','context_alert':'context_alert','calendar_review':'calendar_review','low_alert':'low_alert'}
    f=frame[list(labels)].copy()
    for key in ['prediction','low_probability','context_probability']:f[key]=f[key].map(lambda x:f'{x:.1%}' if pd.notna(x) else t(locale,'missing'))
    f['prediction_route']=f.prediction_route.map(lambda x:t(locale,'route_known' if x=='known' else 'route_unseen'))
    f['calendar_review']=f.calendar_review.map(lambda x:t(locale,'alert_yes' if bool(x) else 'alert_no'))
    f['context_alert']=f.context_alert.map(lambda x:t(locale,'alert_yes' if bool(x) else 'alert_no'))
    f['low_alert']=f.low_alert.map(lambda x:t(locale,'missing' if pd.isna(x) else 'alert_yes' if bool(x) else 'alert_no'))
    return f.rename(columns={key:t(locale,value) for key,value in labels.items()})

def flag_text(row,locale):
    """One readable review flag; the separate model, context and calendar signals stay in the research table."""
    if not bool(row.low_alert):return t(locale,'flag_no')
    reasons=[t(locale,key) for key,on in (('flag_reason_model',row.model_alert),('flag_reason_context',row.context_alert),('flag_reason_holiday',row.calendar_review)) if bool(on)]
    return t(locale,'flag_yes').format(reasons=t(locale,'list_sep').join(reasons))


def queue_display(frame,locale):
    """Primary review queue (heuristic review F1): flag first, six columns, no model internals."""
    import pandas as pd
    labels={'review_flag':'review_flag','room':'room','course_id':'course','course_start':'course_start','course_end':'course_end','prediction':'prediction'}
    f=frame.assign(review_flag=[flag_text(r,locale) for r in frame.itertuples()])[list(labels)].copy()
    f['prediction']=f.prediction.map(lambda x:f'{x:.1%}' if pd.notna(x) else t(locale,'missing'))
    return f.rename(columns={key:t(locale,value) for key,value in labels.items()})


def reason_text(locale,reason):
    value,kind=reason['value'],reason['kind']
    if kind=='percent':shown=f'{value:.1%}' if abs(value)<.1 else f'{value:.0%}'
    elif kind=='points':shown=t(locale,'unit_points').format(v=100*value)
    elif kind=='days':shown=t(locale,'unit_days').format(v=value)
    elif kind=='hours':shown=t(locale,'unit_hours').format(v=value)
    elif kind=='clock':shown=f'{int(value):02d}:{int(round((value%1)*60)):02d}'
    else:shown=f'{value:.0f}'
    return f"{t(locale,reason['feature'])} {shown}"


def plain_summary(locale,score,flagged,reasons,holiday=False,context=False):
    """Plain-language conclusion shown before the technical reconstruction (heuristic review F2)."""
    listed=t(locale,'list_sep').join(reason_text(locale,r) for r in reasons) or t(locale,'plain_none')
    parts=[t(locale,'plain_flagged' if flagged else 'plain_not_flagged').format(score=score,reasons=listed)]
    if holiday:parts.append(t(locale,'plain_holiday'))
    if context:parts.append(t(locale,'plain_context'))
    return ' '.join(parts)


def review_text(locale,row,date_text,flag,conclusion,action_label,note):
    """Readable companion to the JSON review record (heuristic review F10)."""
    lines=[t(locale,"summary_title"),"",f"{t(locale,'date')}: {date_text}",
        f"{t(locale,'summary_class')}: {row.room} · {row.course_id} · {row.course_start}–{row.course_end}",
        f"{t(locale,'review_flag')}: {flag}","",conclusion.replace("**",""),"",
        f"{t(locale,'review_action')}: {action_label}",f"{t(locale,'review_note')}: {note or '—'}","",t(locale,"plain_scope"),t(locale,"export_note")]
    return '\n'.join(lines)+'\n'


def shap_display(frame,locale):
    f=frame.copy()
    f['feature']=f.feature.map(lambda key:t(locale,key) if key in TEXT else key)
    directions={'正相关':'positive','负相关':'negative','常量或无变化，无法计算':'constant'}
    f['direction']=f.direction.map(lambda value:t(locale,directions.get(value,'constant')))
    f['share']=f.share.map(lambda x:f'{x:.1%}')
    return f.rename(columns={key:t(locale,key) for key in f.columns if key in TEXT})
