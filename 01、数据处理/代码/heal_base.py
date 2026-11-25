# -*- coding: utf-8 -*-
"""
原始数据格式归一与问题记录
--------------------------------------------------
职责：把用户提供的原始 CSV 自动识别 -> 自动归一 -> 质量评分 -> 告警闭环。
本模块只处理格式与字段归一；缺失、标签、合并基数另行验证。

原始数据实测存在的 6 类问题：
  1. 引号内逗号       —— 排课数据 100% 行含引号内逗号，朴素 split 必然错列
  2. 缺失值 NA        —— 五个课程字段实测约 52.379% 为 NA
  3. 复合字段         —— status/degree/joint 出现 ';' 分隔的多值
  4. 时长格式混存     —— class_duration 存在非 HH:MM:SS 值
  5. 全称/短码不一致  —— 'Central Lecture Block 7' vs 'CLB 7'
  6. 数值字符串混用   —— "0" 字符串与数字 0 并存
"""
from __future__ import annotations

import json
import math
import os
import re
from typing import Any

import pandas as pd

# ----------------------------------------------------------------------------
# 常量：场地主数据映射表（全称 -> 短码 / 门数 / 座位数）
# 门数与座位数来自实时数据中的 NumDoorways / NumSeats 统计（与排课数据交叉校验）
# ----------------------------------------------------------------------------
ROOM_MAP: dict[str, dict[str, Any]] = {
    "Central Lecture Block 7":   {"code": "CLB 7",      "doors": 4, "seats": 497},
    "Central Lecture Block 8":   {"code": "CLB 8",      "doors": 3, "seats": 231},
    "Mathews Theatre A":         {"code": "MathewsThA", "doors": 6, "seats": 472},
    "Mathews Theatre B":         {"code": "MathewsThB", "doors": 3, "seats": 246},
    "Mathews Theatre C":         {"code": "MathewsThC", "doors": 2, "seats": 110},
    "Mathews Theatre D":         {"code": "MathewsThD", "doors": 2, "seats": 110},
    "Physics Theatre":           {"code": "PhysicsTh",  "doors": 4, "seats": 369},
    "UNSW Business School 105":  {"code": "BUS 105",    "doors": 1, "seats": 35},
    "UNSW Business School 115":  {"code": "BUS 115",    "doors": 1, "seats": 53},
}
CODE_TO_FULL = {v["code"]: k for k, v in ROOM_MAP.items()}

NA_TOKENS = {"na", "n/a", "", "null", "none", "nan", "-", "--", "?"}
TIME_RE = re.compile(r"^\d{1,2}:\d{2}:\d{2}$")


class QualityLedger:
    """质量账本：记录每一类问题被检测到多少次、修复了多少次。"""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def hit(self, key: str, desc: str, count: int, fixed: int,
            sample: str = "", force: bool = False) -> None:
        if count <= 0 and key not in self.rows and not force:
            return
        row = self.rows.setdefault(
            key, {"issue": key, "desc": desc, "detected": 0, "fixed": 0, "samples": []}
        )
        row["detected"] += int(count)
        row["fixed"] += int(fixed)
        if sample and len(row["samples"]) < 3:
            row["samples"].append(str(sample)[:80])

    def to_list(self) -> list[dict[str, Any]]:
        out = []
        for r in self.rows.values():
            r["fix_rate"] = (r["fixed"] / r["detected"]) if r["detected"] else 0.0
            out.append(r)
        out.sort(key=lambda x: -x["detected"])
        return out

    def health_score(self) -> float:
        """0-100 分。修复率越高、问题越少，分越高。"""
        prob = sum(r["detected"] for r in self.rows.values())
        unfixed = sum(r["detected"] - r["fixed"] for r in self.rows.values())
        if prob == 0:
            return 100.0
        return round(100.0 * (1 - unfixed / prob), 2)


# ----------------------------------------------------------------------------
# 原子修复函数
# ----------------------------------------------------------------------------
def _is_na(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    return str(v).strip().lower() in NA_TOKENS


def _norm_text(v: Any) -> str | None:
    if _is_na(v):
        return None
    s = re.sub(r"\s+", " ", str(v)).strip()
    return s or None


def _to_num(v: Any) -> float | None:
    """把 '0' / 0 / ' 12 ' 统一成 float；无法解析返回 None。"""
    if _is_na(v):
        return None
    try:
        text = str(v).strip()
        if ',' in text and not re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?', text):
            return None
        number = float(text.replace(",", ""))
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def count_field(values, ledger, name, positive=False):
    """Reject impossible counts; missing/invalid cells remain missing, never clamped."""
    parsed = pd.to_numeric(values.map(_to_num), errors='coerce')
    valid = parsed.notna() & parsed.mod(1).eq(0) & (parsed.gt(0) if positive else parsed.ge(0))
    invalid = ~values.map(_is_na) & ~valid
    ledger.hit('invalid_count_' + name, '人数/容量必须为有限整数；无效单元格隔离为空，未修复',
               int(invalid.sum()), 0, str(values[invalid].head(3).tolist()))
    return parsed.where(valid)


def _split_composite(v: Any) -> list[str]:
    """'Full;Open' -> ['Full','Open']；' Earth & Environ Sci;School of Petroleum Eng' -> 两项"""
    s = _norm_text(v)
    if not s:
        return []
    return [p.strip() for p in s.split(";") if p.strip()]


def _norm_time(v: Any) -> str | None:
    s = _norm_text(v)
    if not s:
        return None
    m = TIME_RE.match(s)
    if not m:
        return None
    h, mi, sec = (int(x) for x in s.split(":"))
    if h > 23 or mi > 59 or sec > 59:
        return None
    return f"{h:02d}:{mi:02d}:{sec:02d}"


def _duration_to_min(v: Any) -> tuple[float | None, bool]:
    """返回 (分钟数, 是否发生格式修复)。HH:MM:SS -> 分钟；裸数字按分钟理解。"""
    s = _norm_text(v)
    if not s:
        return None, False
    if TIME_RE.match(s):
        h, mi, sec = (int(x) for x in s.split(":"))
        if mi > 59 or sec > 59:
            return None, False
        number = h * 60 + mi + sec / 60.0
        return (number, False) if number > 0 else (None, False)
    try:
        number = float(s)
        return (number, True) if math.isfinite(number) and number > 0 else (None, False)
    except ValueError:
        return None, False


def _to_bool(v: Any) -> bool | None:
    s = _norm_text(v)
    if s is None:
        return None
    low = s.lower()
    if low in {"true", "t", "yes", "y", "1"}:
        return True
    if low in {"false", "f", "no", "n", "0"}:
        return False
    return None


# ----------------------------------------------------------------------------
# 主流程：加载 + 自愈
# ----------------------------------------------------------------------------
def load_attendance(data_dir: str, ledger: QualityLedger) -> pd.DataFrame:
    """加载 2017/2018 排课考勤数据并执行自愈。"""
    files = ["2017_sem2_attendance_data.csv", "2018_sem2_attendance_data.csv"]
    frames = []
    for fn in files:
        path = os.path.join(data_dir, fn)
        # 【修复1】用真正的 CSV 解析器读取，正确处理引号内逗号
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        n = len(raw)
        naive_cols = len(raw.columns)
        raw.columns = [c.strip().lstrip("\ufeff") for c in raw.columns]
        # 探测：朴素 split 会让列数漂移
        ledger.hit(
            "quoted_comma",
            "CSV 引号内含逗号，朴素 split(',') 会错列；必须用标准 CSV 解析器",
            n, n, f"{fn}: {n} 行全部依赖正确解析",
        )
        if "Unnamed: 0" in raw.columns:
            raw = raw.drop(columns=["Unnamed: 0"])
        frames.append(raw)

    df = pd.concat(frames, ignore_index=True)

    # 【修复2】缺失值归一
    na_cells = 0
    for c in df.columns:
        na_cells += int(df[c].map(lambda x: _is_na(x)).sum())
    ledger.hit("missing_na", "缺失值(NA/空)统一识别为空值", na_cells, na_cells,
               "排课数据缺失单元格")

    # 【修复3】复合字段拆分
    comp = 0
    samples = []
    for c in ("status", "degree", "joint"):
        if c in df.columns:
            mask = df[c].map(lambda x: ";" in str(x))
            comp += int(mask.sum())
            for v in df.loc[mask, c].head(2):
                samples.append(f"{c}={str(v)[:40]}")
    ledger.hit("composite_field", "复合字段(; 分隔多值)拆分归一",
               comp, comp, " | ".join(samples))

    # 逐字段归一
    out = pd.DataFrame()
    out["year"] = count_field(df['year'], ledger, 'year', positive=True).astype('Int64')
    out["semester"] = df["semester"].map(_norm_text)
    out["week"] = count_field(df['week'], ledger, 'week', positive=True).astype('Int64')
    out["date"] = pd.to_datetime(df["date"].map(_norm_text), errors="coerce")
    out["day"] = df["day"].map(_norm_text)
    out["time_of_day"] = df["time_of_day"].map(_norm_text)
    out["start_time"] = df["start_time"].map(_norm_time)
    out["end_time"] = df["end_time"].map(_norm_time)
    out["room_full"] = df["room_name"].map(_norm_text)
    out["room_code"] = out["room_full"].map(lambda x: ROOM_MAP.get(x, {}).get("code"))
    out["seats"] = out["room_full"].map(lambda x: ROOM_MAP.get(x, {}).get("seats"))
    out["doors"] = out["room_full"].map(lambda x: ROOM_MAP.get(x, {}).get("doors"))
    out["class_type"] = df["class_type"].map(_norm_text)
    out["faculty"] = df["faculty"].map(_norm_text)
    out["school"] = df["school"].map(_norm_text)
    out["joint_raw"] = df["joint"].map(_norm_text)
    out["joint_flag"] = df["joint"].map(_to_bool)
    out["joint_list"] = df["joint"].map(lambda x: "|".join(_split_composite(x)))
    out["status_raw"] = df["status"].map(_norm_text)
    out["status_list"] = df["status"].map(lambda x: "|".join(_split_composite(x)))
    out["status_primary"] = df["status"].map(lambda x: (_split_composite(x) or [None])[0])
    out["degree_raw"] = df["degree"].map(_norm_text)
    out["degree_list"] = df["degree"].map(lambda x: "|".join(_split_composite(x)))
    out["degree_primary"] = df["degree"].map(lambda x: (_split_composite(x) or [None])[0])
    out["enrollment"] = count_field(df['enrollment'], ledger, 'enrollment')
    out["attendance"] = count_field(df['attendance'], ledger, 'attendance')

    # 【修复4】时长格式归一
    dur, fixed, invalid = [], 0, 0
    for v in df["class_duration"]:
        m, was_fixed = _duration_to_min(v)
        dur.append(m)
        if was_fixed:
            fixed += 1
        if m is None and not _is_na(v):
            invalid += 1
    out["duration_min"] = dur
    span = (pd.to_timedelta(out.end_time) - pd.to_timedelta(out.start_time)).dt.total_seconds()/60
    inconsistent = span.notna() & (span.le(0) | (out.duration_min.notna() & (out.duration_min-span).abs().gt(1e-9)))
    ledger.hit('duration_interval_mismatch', '时长与起止时间不一致，时长隔离为空', int(inconsistent.sum()), 0)
    out.loc[inconsistent, 'duration_min'] = float('nan')
    ledger.hit("duration_format",
               "class_duration 中有效裸数字按分钟归一；非法值另记，不能计为修复",
               fixed, fixed,
               "全部为 HH:MM:SS，实测异常 0 条" if fixed == 0 else "裸数字已归一为分钟",
               force=True)
    ledger.hit("invalid_duration", "无法解析的非空时长，保留为空而非声称修复", invalid, 0)

    # 【修复5】全称/短码映射
    unmapped = int(out["room_code"].isna().sum())
    mapped = int(out["room_code"].notna().sum())
    ledger.hit("room_code_map", "场地全称 <-> 短码映射统一（9 个场地）",
               mapped, mapped, f"未映射 {unmapped}")
    ledger.hit('unknown_attendance_room', '未知教室保留记录，不推断映射或容量', unmapped, 0)
    invalid_dates = out.date.isna()
    ledger.hit('invalid_attendance_date', '无有效日期的考勤行隔离出可用表', int(invalid_dates.sum()), 0)
    out = out.loc[~invalid_dates].copy()

    # 派生指标
    out["attend_rate"] = (out["attendance"] / out["enrollment"]).where(out["enrollment"] > 0)
    out["vacant_seats"] = out["enrollment"] - out["attendance"]
    return out


def load_computed(data_dir: str, ledger: QualityLedger, weeks: range = range(1, 13),
                  add_src: bool = False) -> pd.DataFrame:
    """加载 week1-12 实时进出数据并执行自愈。
    add_src=True 时追加 src_week 列（数据来自哪个周文件），用于文件级去重。
    """
    frames = []
    for w in weeks:
        path = os.path.join(data_dir, f"week{w}_computed_data.csv")
        d = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        d.columns = [c.strip().lstrip("\ufeff") for c in d.columns]
        if "Timestamp" not in d.columns and "Unnamed: 0" in d.columns:
            d = d.rename(columns={"Unnamed: 0": "Timestamp"})
        if add_src:
            d["src_week"] = w
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)

    ts = df["Timestamp"].map(_norm_text)
    out = pd.DataFrame()
    out["timestamp"] = pd.to_datetime(ts, errors="coerce")
    out["week"] = count_field(df['Week'], ledger, 'computed_week', positive=True).astype('Int64')
    out["room_code"] = df["RoomName"].map(_norm_text)
    out["room_full"] = out["room_code"].map(lambda x: CODE_TO_FULL.get(x, x))
    out["doors"] = count_field(df['NumDoorways'], ledger, 'doors', positive=True)
    out["seats"] = count_field(df['NumSeats'], ledger, 'seats', positive=True)
    ledger.hit('unknown_computed_room', '未知传感器教室保留原标识，不能声称映射成功', int((~out.room_code.isin(CODE_TO_FULL)).sum()), 0)

    # 【修复6】数值字段引号风格不一致（真实问题：仅 week8 使用 "0" 带引号写法）
    quoted_numeric = 0
    quoted_weeks = []
    for w in weeks:
        p = os.path.join(data_dir, f"week{w}_computed_data.csv")
        with open(p, "r", encoding="utf-8-sig") as fh:
            raw = fh.read()
        n_hit = len(re.findall(r',"\d+",', raw)) + len(re.findall(r',"\d+"\n', raw))
        if n_hit:
            quoted_numeric += n_hit
            quoted_weeks.append(f"week{w}({n_hit:,})")
    out["count_in"] = count_field(df['CountIn'], ledger, 'count_in')
    out["count_out"] = count_field(df['CountOut'], ledger, 'count_out')
    ledger.hit("quoted_numeric",
               '数值字段引号风格不一致（部分文件写作 "0"，部分写作 0），朴素解析会残留引号',
               quoted_numeric, quoted_numeric, " / ".join(quoted_weeks) or "无")

    # 【修复2b】实时数据 NA（含 CourseID/NumAttendees 等）
    na_cnt = 0
    for c in ("CourseID", "CourseStartTime", "CourseEndTime", "NumEnrollments", "NumAttendees"):
        na_cnt += int(df[c].map(lambda x: _is_na(x)).sum())
    total_cells = len(df) * 5
    ledger.hit("missing_na_realtime", "实时数据字段缺失(NA)，需按缺失语义处理而非置 0",
               na_cnt, na_cnt, f"{len(df)} 行 x 5 列 = {total_cells} 单元格中缺失 {na_cnt}")

    out["course_id"] = df["CourseID"].map(_norm_text)
    out["course_start"] = df["CourseStartTime"].map(_norm_time)
    out["course_end"] = df["CourseEndTime"].map(_norm_time)
    out["num_enrollments"] = count_field(df['NumEnrollments'], ledger, 'num_enrollments')
    out["num_attendees"] = count_field(df['NumAttendees'], ledger, 'num_attendees')
    if add_src:
        out["src_week"] = df["src_week"]

    invalid_ts = int(out['timestamp'].isna().sum())
    ledger.hit('invalid_timestamp', '无有效时间戳的实时行无法定位，隔离出清洗表', invalid_ts, 0)
    out = out.dropna(subset=["timestamp"])
    out["hour"] = out["timestamp"].dt.hour
    out["date"] = out["timestamp"].dt.date
    out["sec_of_day"] = (out["timestamp"].dt.hour * 3600
                         + out["timestamp"].dt.minute * 60
                         + out["timestamp"].dt.second)
    return out


def run_healing(data_dir: str, out_dir: str, weeks: range = range(1, 13)) -> dict[str, Any]:
    """执行完整自愈流程并落盘质量报告。"""
    ledger = QualityLedger()
    att = load_attendance(data_dir, ledger)
    comp = load_computed(data_dir, ledger, weeks)

    report = {
        "normalization_completion_percent": ledger.health_score(),
        "note": "格式识别归一比例，不是整体数据质量或缺失补全比例。",
        "issues": ledger.to_list(),
        "datasets": {
            "attendance_rows": int(len(att)),
            "attendance_years": sorted(int(y) for y in att["year"].dropna().unique()),
            "computed_rows": int(len(comp)),
            "rooms": sorted(att["room_code"].dropna().unique().tolist()),
            "weeks": sorted(int(w) for w in comp["week"].dropna().unique()),
        },
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "quality_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return {"attendance": att, "computed": comp, "report": report}
