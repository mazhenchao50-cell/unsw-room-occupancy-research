"""Offline UI catalog; each row contains zh, en, ko, ja translations."""
LANGUAGES={'zh':'中文','en':'English','ko':'한국어','ja':'日本語'}
TEXT={
 'needs_title':('1 · 填写使用需求','1 · Set your requirements','1 · 이용 조건 입력','1 · 利用条件を入力'),
 'query_summary':('{date} · {start}–{end} · 需要{seats}个座位','{date} · {start}–{end} · {seats} seats needed','{date} · {start}–{end} · 필요 좌석 {seats}석','{date} · {start}–{end} · 必要座席数 {seats}席'),
 'result_counts':('符合座位要求：{eligible}间；其中课表空档{gaps}间、有课冲突{conflicts}间、信息不足{unknown}间。最多展示5间候选。','{eligible} rooms meet the seat requirement: {gaps} timetable gaps, {conflicts} schedule conflicts, {unknown} with insufficient records. Up to 5 candidates are shown.','좌석 조건 충족 {eligible}개: 시간표상 빈 시간 {gaps}개, 수업 충돌 {conflicts}개, 정보 부족 {unknown}개입니다. 후보는 최대 5개 표시합니다.','座席条件を満たす教室は{eligible}室：時間割の空き{gaps}室、授業との重複{conflicts}室、情報不足{unknown}室。候補を最大5室表示します。'),
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
 'later_found':('当天稍晚可试 {time}：找到{count}间课表空档候选。人数和时长保持不变；只检查随后4小时内每15分钟的开始时刻。','Try {time} on the same day: {count} timetable-gap candidates. Seats and duration stay unchanged. Search covers 15-minute start times within the next 4 hours.','같은 날 {time}에 시간표상 후보 {count}개가 있습니다. 좌석 수와 이용 시간은 유지하며 이후 4시간의 15분 간격 시작 시각만 확인합니다.','同日の{time}なら時間割上の候補が{count}室あります。座席数と利用時間は変えず、その後4時間内の15分刻みの開始時刻を調べます。'),
 'try_later':('改查 {time}','Search at {time}','{time}로 조회','{time}で再検索'),
 'no_later':('当天随后4小时内、按15分钟间隔检查的开始时刻也没有匹配候选。可调整日期或需求；这不代表已确认全部教室有人。','No match at the checked 15-minute start times within the next 4 hours of this date. Try another date or requirements; this does not confirm every room is occupied.','같은 날 이후 4시간의 15분 간격 시작 시각에서도 조건에 맞는 후보가 없습니다. 날짜나 조건을 바꿔 보세요. 모든 강의실이 사용 중임을 뜻하지 않습니다.','同日のその後4時間内、15分刻みで確認した開始時刻にも候補がありません。日付や条件を変更してください。すべての教室が使用中と確認されたわけではありません。'),
 'research_toggle':('显示预测与研究验证详情','Show predictions and research validation','예측 및 연구 검증 상세 보기','予測と研究検証の詳細を表示'),
 'research_separation':('以下预测只描述已排课会话，不参与课表空档候选排序。切换模型不会取消已排课冲突。','Predictions below describe scheduled classes only and do not rank timetable-gap candidates. Changing models never removes schedule conflicts.','아래 예측은 예정 수업에만 해당하며 빈 시간 후보 순위에는 사용하지 않습니다. 모델을 바꿔도 수업 충돌은 해제되지 않습니다.','以下の予測は予定された授業のみが対象で、空き時間候補の順位には使いません。モデルを変えても授業との重複は解除されません。'),
 'research_unavailable':('课表查询仍可使用；预测详情暂不可用，请联系维护者检查研究产物。','Timetable search remains available. Prediction details are unavailable; ask the maintainer to check the research outputs.','시간표 조회는 계속 사용할 수 있습니다. 예측 상세는 준비되지 않았으므로 관리자에게 연구 결과 파일 확인을 요청하세요.','時間割検索は引き続き利用できます。予測の詳細は表示できないため、管理者に研究結果ファイルの確認を依頼してください。'),
 'prediction_mode':('预测方案','Prediction mode','예측 방식','予測方式'),
 'system_current':('现用方案','Current system','현재 방식','現行方式'),
 'system_unified':('分场景研究方案','Routed research system','상황별 연구 방식','状況別の研究方式'),
 'unified_title':('有课会话占用与低利用率预测','Scheduled occupancy and low-utilization predictions','수업 점유율 및 저이용 예측','授業の利用率と低利用の予測'),
 'unified_scope':('研究候选：已见教室的低利用率分类器按历史验证选择模型，并用测试周前两周校准阈值；未见教室用静态模型。第12周仅22条提示全命中，但召回率39.3%（漏报34条）；第8至12周合并精确率53.7%，未达到同一精确率门槛。低利用不等于无人或可释放教室。','Research candidate: the known-room low-use classifier selects its model on earlier data and calibrates its threshold on the two prior weeks; unseen rooms use a static model. Week 12 returned 22 alerts, all correct, but recall was 39.3% (34 misses). Pooled precision across weeks 8–12 was 53.7%, below the same precision gate. Low use does not mean vacant or releasable.','연구 후보입니다. 기존 강의실 저이용 분류기는 과거 검증 자료로 모델을 선택하고 직전 2주 자료로 임계값을 보정하며, 새 강의실은 정적 모델을 사용합니다. 12주차 알림 22건은 모두 맞았지만 재현율은 39.3%(34건 미탐)였습니다. 8~12주 통합 정밀도는 53.7%로 같은 기준에 미달합니다. 저이용은 공실이나 해제 가능을 뜻하지 않습니다.','研究候補です。既知教室の低利用分類器は過去データでモデルを選び、直前2週で閾値を調整します。未知教室には静的モデルを使います。第12週は22件すべて的中しましたが、再現率は39.3%（34件見逃し）でした。第8～12週の統合適合率は53.7%で同じ基準に届きません。低利用は空室や解放可能を意味しません。'),
 'unified_cutoff':('仅预测训练和校准截止日 {date} 之后的会话。','Predictions are restricted to sessions after fitting and calibration cutoff {date}.','학습 및 보정 마감일 {date} 이후 수업만 예측합니다.','学習・較正の最終日 {date} より後の授業のみ予測します。'),
 'unified_risk':('第12周低利用率提示：命中{tp}、误报{fp}、漏报{fn}；精确率{precision}，召回率{recall}。数值过线不代表充分检出。','Week 12 low-use alerts: {tp} matches, {fp} false alerts, {fn} misses; precision {precision}, recall {recall}. Passing a numeric threshold does not mean adequate detection.','12주차 저이용 알림: 적중 {tp}, 오탐 {fp}, 미탐 {fn}; 정밀도 {precision}, 재현율 {recall}. 수치 기준 충족이 충분한 검출을 뜻하지 않습니다.','第12週の低利用警告：一致{tp}、誤検出{fp}、見逃し{fn}。適合率{precision}、再現率{recall}。数値基準の達成は十分な検出を意味しません。'),
 'unified_unavailable':('研究方案的模型、数据或源码与验证记录不一致，请重建后再使用。','Research model, data or source differs from its verified record. Rebuild before use.','연구 모델, 데이터 또는 코드가 검증 기록과 다릅니다. 다시 생성한 후 사용하세요.','研究モデル、データまたはコードが検証記録と一致しません。再構築してから使用してください。'),
 'unified_explain':('下表只解释已见教室的LightGBM占用率预测；不解释独立低利用率分类器或新教室静态模型。','The table explains only known-room LightGBM occupancy predictions, not the separate low-use classifier or unseen-room static model.','아래 표는 기존 강의실의 LightGBM 점유율 예측만 설명하며 별도 저이용 분류기나 새 강의실 정적 모델은 설명하지 않습니다.','下表は既知教室のLightGBM利用率予測のみを説明し、独立した低利用分類器や未知教室の静的モデルは説明しません。'),
 'route_label':('预测分工','Prediction branch','예측 분기','予測の分岐'),
 'route_known':('已见教室','Known room','기존 강의실','既知の教室'),
 'route_unseen':('未见教室','Unseen room','새 강의실','未知の教室'),
 'low_score':('低利用率模型得分','Low-use model score','저이용 모델 점수','低利用モデルスコア'),
 'low_alert':('低利用率提示','Low-use alert','저이용 알림','低利用警告'),
 'cold_start_experiment':('新教室预测研究进展','Unseen-room prediction study','새 강의실 예측 연구','未知の教室の予測研究'),
 'cold_start_scope':('此处是独立候选的历史留一教室验证，尚未替换现用模型。选参数时也按教室隔离；不能据此保证新校园或未来表现。','This is a separate candidate evaluated retrospectively with held-out rooms. It has not replaced the current model. Model selection also separates rooms; new-campus or future performance is not guaranteed.','별도 후보 모델의 과거 강의실 제외 검증 결과이며 현재 모델을 대체하지 않았습니다. 설정 선택에서도 강의실을 분리했습니다. 새 캠퍼스나 미래 성능을 보장하지 않습니다.','独立した候補の教室単位の履歴検証で、現行モデルは置き換えていません。設定の選択でも教室を分離しています。別キャンパスや将来の性能は保証しません。'),
 'cold_start_summary':('九间教室平均RMSE：{rmse}；同方案随机切分RMSE：{random}。数值过线仍需结合误差范围判断。','Mean RMSE across nine rooms: {rmse}; same-method random-split RMSE: {random}. Numeric thresholds must be interpreted with uncertainty.','9개 강의실 평균 RMSE: {rmse}, 같은 방법의 무작위 분할 RMSE: {random}. 수치 기준 충족 여부는 불확실성과 함께 해석해야 합니다.','9教室の平均RMSE：{rmse}、同じ方法のランダム分割RMSE：{random}。数値基準の達成は不確実性と併せて判断してください。'),
 'setup_required':('演示所需的数据或模型尚未准备完成，请联系维护者完成初始化后重试。','Required demo data or models are not ready. Ask the maintainer to finish setup and retry.','시연에 필요한 데이터 또는 모델이 준비되지 않았습니다. 관리자에게 초기 설정 완료를 요청한 후 다시 시도해 주세요.','デモに必要なデータまたはモデルが未準備です。管理者に初期設定を依頼してから再試行してください。'),
 'title':('课表空档查询 · 历史演示','Find timetable gaps · Historical demo','시간표 빈 시간 찾기 · 과거 데이터 데모','時間割の空き検索 · 履歴デモ'),
 'intro':('先填写时段和座位需求，再查看候选与核查事项。当前使用UNSW 2017年第12周记录，不提供今天的教室可用性或预约服务。','Enter your time and seat needs, then review candidates and next steps. This uses UNSW 2017 week 12 records; it does not provide today’s availability or bookings.','시간과 좌석 조건을 입력한 후 후보와 확인 사항을 보세요. UNSW 2017년 12주차 기록을 사용하며 오늘의 이용 가능 여부나 예약을 제공하지 않습니다.','時間と座席数を入力し、候補と確認事項を見てください。UNSWの2017年第12週の記録を使用しており、今日の空室情報や予約サービスではありません。'),
 'date':('历史日期','Historical date','과거 날짜','履歴の日付'),
 'time_basis':('日期与时刻沿用UNSW原始数据的校园当地时间，未转换为你当前所在地时间。','Dates and times follow the original UNSW campus-local records; they are not converted to your current local time.','날짜와 시각은 UNSW 원본 데이터의 캠퍼스 현지 시간을 따르며 사용자 지역 시간으로 변환하지 않습니다.','日時はUNSW元データのキャンパス現地時刻で表示し、現在地の時刻には変換していません。'),
 'start':('开始时间','Start time','시작 시각','開始時刻'),
 'duration':('使用时长（分钟）','Duration (minutes)','사용 시간(분)','利用時間（分）'),
 'capacity':('所需座位','Seats needed','필요 좌석 수','必要な座席数'),
 'midnight':('使用时段不能跨越当天午夜，请提前开始时间或缩短使用时长。','The interval cannot cross midnight. Choose an earlier start or shorter duration.','사용 시간이 자정을 넘을 수 없습니다. 시작 시각을 앞당기거나 사용 시간을 줄여 주세요.','利用時間は日付をまたげません。開始時刻を早めるか利用時間を短くしてください。'),
 'query_error':('无法完成查询，请检查时间、时长和座位需求。','Unable to complete the query. Check the time, duration and seats.','조회할 수 없습니다. 시각, 사용 시간, 좌석 수를 확인해 주세요.','検索できません。時刻、利用時間、座席数を確認してください。'),
 'top':('2 · 查看课表空档候选','2 · Review timetable-gap candidates','2 · 시간표상 빈 시간 후보 확인','2 · 時間割の空き候補を確認'),
 'ranking':('按满足需求后的座位数升序排列。候选均需现场核实占用与开放权限；有课时即使预测低利用率也不推荐。','Ranked by smallest sufficient capacity. Check actual occupancy and access permission. Scheduled rooms remain blocked even with low predicted utilization.','필요 좌석 수를 충족하는 작은 강의실부터 표시합니다. 실제 점유와 개방 여부를 확인해야 합니다. 예측 이용률이 낮아도 수업이 있는 강의실은 추천하지 않습니다.','必要座席数を満たす小さな教室から表示します。現地の利用状況と使用許可を確認してください。予測利用率が低くても授業のある教室は推薦しません。'),
 'empty':('当前条件下没有课表空档候选。可调整时间或座位需求；这不代表所有教室都已确认有人。','No timetable-gap candidates match. Try another time or capacity. This does not prove that every room is occupied.','조건에 맞는 후보가 없습니다. 시간이나 좌석 수를 조정해 보세요. 모든 강의실에 사람이 있다는 뜻은 아닙니다.','条件に合う候補がありません。時刻や座席数を変更してください。すべての教室に人がいると確認されたわけではありません。'),
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
 'unknown':('课表信息不足','Insufficient schedule data','시간표 정보 부족','時間割の情報不足'),
 'gap':('课表空档，现场待核实','Timetable gap; check on site','시간표상 빈 시간, 현장 확인 필요','時間割は空き、現地確認が必要'),
 'unverified':('未核实','Not verified','미확인','未確認'), 'verified':('已核实','Verified','확인됨','確認済み'),
 'conflict_reason':('课表冲突，不推荐','Scheduled conflict; not recommended','수업 시간 충돌로 추천하지 않음','授業と重複するため推薦対象外'),
 'unknown_reason':('课表信息不足，不能推断为空闲','Insufficient schedule data; vacancy cannot be inferred','시간표 정보 부족으로 공실 판단 불가','時間割情報が不足しており空室と判断できません'),
 'gap_reason':('仅为课表空档候选，现场占用及开放权限待核实','Timetable-gap candidate only; check occupancy and access permission','시간표상 빈 시간 후보이며 실제 점유와 사용 허가 확인 필요','時間割の空き時間候補です。利用状況と使用許可を確認してください'),
 'course':('课程编号','Course ID','과목 ID','科目ID'),
 'course_start':('课程开始','Class start','수업 시작','授業開始'),
 'course_end':('课程结束','Class end','수업 종료','授業終了'),
 'prediction':('预测峰值占用率','Predicted peak occupancy','예측 최대 점유율','予測最大利用率'),
 'probability':('零峰值模型得分（未校准）','Zero-peak model score (uncalibrated)','최대 관측 인원 0명 모델 점수(미보정)','観測最大人数ゼロのモデルスコア（未較正）'),
 'alert':('零峰值提示','Zero-peak alert','최대 관측 인원 0명 알림','観測最大人数ゼロの警告'),
 'alert_yes':('风险提示，仍不可释放','Risk flagged; do not release','위험 감지, 사용 해제 불가','リスクあり、予約解除不可'),
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
 'week':('学期周次','Semester week','학기 주차','学期の週'),
 'model':('模型','Model','모델','モデル'),
 'original_model':('原模型','Original model','기존 모델','元のモデル'),
 'candidate_model':('改进候选','Candidate model','개선 후보','改善候補'),
 'precision':('精确率','Precision','정밀도','適合率'),
 'recall':('召回率','Recall','재현율','再現率'),
 'fp':('误报数','False alerts','오탐 수','誤検出数'),
 'fn':('漏报数','Missed events','미탐 수','見逃し数'),
}
CATALOG={locale:{key:values[i] for key,values in TEXT.items()} for i,locale in enumerate(LANGUAGES)}

def t(locale,key):
    return CATALOG.get(locale,CATALOG['en'])[key]

def room_display(frame,locale):
    f=frame.copy()
    statuses={'scheduled_conflict':'conflict','schedule_unknown':'unknown','timetable_gap_occupancy_unknown':'gap'}
    f['reason']=f.status.map(lambda s:t(locale,statuses.get(s,'unknown')+'_reason'))
    f['status']=f.status.map(lambda s:t(locale,statuses.get(s,'unknown')))
    f['verified_available']=f.verified_available.map(lambda value:t(locale,'verified' if value==True else 'unverified'))
    return f.rename(columns={key:t(locale,target) for key,target in {'room':'room','seats':'seats','status':'status','verified_available':'availability','reason':'reason'}.items()})

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
            'prediction_route':'route_label','low_probability':'low_score','low_alert':'low_alert'}
    f=frame[list(labels)].copy()
    for key in ['prediction','low_probability']:f[key]=f[key].map(lambda x:f'{x:.1%}' if pd.notna(x) else t(locale,'missing'))
    f['prediction_route']=f.prediction_route.map(lambda x:t(locale,'route_known' if x=='known' else 'route_unseen'))
    f['low_alert']=f.low_alert.map(lambda x:t(locale,'missing' if pd.isna(x) else 'alert_yes' if bool(x) else 'alert_no'))
    return f.rename(columns={key:t(locale,value) for key,value in labels.items()})

def shap_display(frame,locale):
    f=frame.copy()
    f['feature']=f.feature.map(lambda key:t(locale,key) if key in TEXT else key)
    directions={'正相关':'positive','负相关':'negative','常量或无变化，无法计算':'constant'}
    f['direction']=f.direction.map(lambda value:t(locale,directions.get(value,'constant')))
    f['share']=f.share.map(lambda x:f'{x:.1%}')
    return f.rename(columns={key:t(locale,key) for key in f.columns if key in TEXT})
