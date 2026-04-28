#!/usr/bin/env python3
"""
杭州 2026 中考志愿填报系统 — 十三中专属版
基于真实政策数据 + 校内排名映射 + 成绩回归预测
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════
# 📊 2026 杭州市中考政策数据库（杭州教育发布官方数据）
# ═══════════════════════════════════════════════

POLICY_2026 = {
    "city_graduates": 44500,
    "city_quota_total": 9021,
    "total_score": 650,
    "subjects": {"语文": 120, "数学": 120, "英语": 120, "科学": 160, "社会": 100, "体育": 30},
    "exam_date": ("6月20日", "6月21日"),
    "quota_apply_date": ("5月29日 8:00", "5月30日 18:00"),
    "quota_max_schools": 5,
    "central_first_max_schools": 10,
    "system_url": "www.hzjyks.net",
}

THIRTEEN_SCHOOL = {
    "name": "杭州十三中（教育集团）",
    "district": "西湖区",
    "grade_2025": 1044,
    "grade_2026": 1132,
    "quota_2025": 206,
    "quota_2026_est": 229,
    "quota_ratio_2025": 0.197,
    "quota_ratio_2026_est": 0.2027,
    "zhonggao_rate": 0.2864,    # 重高率 28.64%
    "yougao_rate": 0.71,        # 优高率 71%+
    "zhonggao_count_2025": 299,
}


# ═══════════════════════════════════════════════
# 🏫 学校数据库 — 2026 分配生计划 + 录取参考排名
# ═══════════════════════════════════════════════

@dataclass
class School:
    name: str
    category: str       # "重高" | "优高"
    tier: str           # "S" | "A" | "B" | "C" | "D"
    plan_total_2026: int
    quota_ratio: float  # 70% for old schools, 40% for new branches
    quota_slots_2026: int    # 分配生名额
    rank_ref_2025: Optional[int] = None  # 2025十三中录取校内排名参考
    note: str = ""


# 2026 各校分配生名额（十三中依据官方比例计算）
SCHOOLS_2026 = [
    # ── 重高 ──
    School("杭二中滨江",    "重高", "S", 672,  0.70, 12,   15, "杭州最顶尖，清北录取大户"),
    School("学军中学西溪",  "重高", "S", 672,  0.70, 12,   27, "与杭二并列顶尖，竞赛强校"),
    School("杭高贡院",      "重高", "A", 624,  0.70, 12,   73, "百年名校，文科见长"),
    School("十四凤起",      "重高", "A", 576,  0.70, 11,   159, "理科强校，竞赛突出"),
    School("学军紫金港",    "重高", "A", 480,  0.40, 7,    111, "学军新校区，上升快"),
    School("杭四下沙",      "重高", "A", 624,  0.70, 11,   210, "国际化特色"),
    School("浙大附玉泉",    "重高", "B", 576,  0.70, 11,   230, "浙大资源支持"),
    School("长河高中",      "重高", "B", 528,  0.70, 11,   295, "滨江区旗舰，可捡漏"),
    School("杭高钱江",      "重高", "B", 480,  0.40, 7,    306, "杭高分校，可捡漏3分"),
    School("杭师附中",      "重高", "B", 528,  0.70, 13,   250, "师范类底子"),
    School("杭二高新",      "重高", "B", 864,  0.40, 9,    None, "2026新增！杭二分校"),
    School("浙大附实验",    "重高", "B", 672,  0.40, 7,    None, "2026新增！浙大附分校"),
    School("学军海创园",    "重高", "C", 480,  0.40, 6,    350, "学军集团"),
    School("杭二钱江",      "重高", "C", 432,  0.40, 4,    380, "杭二集团"),
    School("杭高钱塘",      "重高", "C", 480,  0.40, 10,   370, "杭高集团"),
    School("杭高临平",      "重高", "C", 432,  0.40, 4,    420, "杭高集团新校"),
    School("十四康桥",      "重高", "C", 432,  0.40, 8,    400, "十四中分校"),
    School("浙大附丁兰",    "重高", "C", 432,  0.40, 7,    430, "浙大附分校"),
    School("杭四江东",      "重高", "C", 432,  0.40, 7,    450, "杭四集团"),
    School("杭二东河",      "重高", "C", 432,  0.40, 5,    500, "杭二集团"),
    School("杭二富春",      "重高", "C", 432,  0.40, 4,    480, "杭二集团"),
    School("学军桐庐",      "重高", "C", 432,  0.40, 4,    500, "学军集团"),
    School("十四青山湖",    "重高", "C", 432,  0.40, 4,    520, "十四中分校"),
    School("长河二高",      "重高", "C", 432,  0.40, 10,   550, "长河分校"),

    # ── 优高 ──
    School("源清中学",      "优高", "C", 480,  0.40, 8,    600, "拱墅区优高"),
    School("杭七转塘",      "优高", "C", 480,  0.40, 5,    650, "美术特色"),
    School("杭师大附二中",  "优高", "C", 432,  0.40, 8,    680, "杭师附分校"),
    School("源清二高",      "优高", "C", 432,  0.40, 7,    700, "源清分校"),
    School("杭四吴山",      "优高", "D", 432,  0.40, 4,    750, "杭四分校"),
    School("绿城育华",      "优高", "D", 200,  0.40, 2,    800, "民办 26000/学期"),
]


# ═══════════════════════════════════════════════
# 🧮 预测引擎
# ═══════════════════════════════════════════════

@dataclass
class Student:
    """学生数据模型"""
    grade_size: int = 1132

    # 成绩数据（需要用户输入）
    exams: dict = field(default_factory=dict)  # {"九上": (得分, 总分, 校排), "一模": ...}

    # 预测结果
    predicted_score: Optional[float] = None
    predicted_rank_school: Optional[int] = None
    predicted_rank_city_pct: Optional[float] = None

    def add_exam(self, name: str, score: float, total: int, school_rank: int):
        self.exams[name] = {
            "score": score,
            "total": total,
            "pct": score / total,
            "rank": school_rank,
        }

    # ═══════════════════════════════════════════════
# 2025 一模基准（用于校准预测）
# ═══════════════════════════════════════════════

BENCHMARK_2025 = {
    "top3_line": 582,       # 前三所线（一模分）
    "top3_count": 112,      # 前三所在校人数
    "zhonggao_line": 565,   # 重高线
    "zhonggao_count": 354,  # 重高在校人数
}

# 预测权重（教育教学研究常用）
PREDICT_WEIGHTS = {"一模": 0.40, "二模": 0.30, "三模": 0.30}


def predict_score_weighted(exams: dict) -> dict:
    """
    加权中考分数预测：一模×40% + 二模×30% + 三模×30%
    缺少的考试自动重新分配权重。
    """
    weighted_pct = 0
    total_weight = 0

    weight_map = {"一模": 0.40, "二模": 0.30, "三模": 0.30}

    for name, w in weight_map.items():
        if name in exams:
            e = exams[name]
            pct = e["score"] / e["total"]
            weighted_pct += pct * w
            total_weight += w

    if total_weight == 0:
        return {"score": 0, "low": 0, "high": 0}

    pct = weighted_pct / total_weight
    score = round(pct * 650)
    margin = 8
    return {"score": score, "low": score - margin, "high": score + margin}


def predict_rank_calibrated(exams: dict, predicted_score: float) -> int:
    """基于排名趋势 + 2025一模基准校准的排名预测"""
    ranks = []
    for key in ["九上期末", "一模", "二模"]:
        if key in exams and "rank" in exams[key]:
            ranks.append(exams[key]["rank"])

    if len(ranks) >= 2:
        dsum = sum(ranks[i] - ranks[i+1] for i in range(len(ranks)-1))
        slope = dsum / (len(ranks) - 1)
        est = max(1, round(ranks[-1] + slope * 0.5))
    else:
        est = THIRTEEN_SCHOOL["grade_2026"]

    # 分数校准
    if predicted_score >= BENCHMARK_2025["top3_line"]:
        est = min(est, BENCHMARK_2025["top3_count"])
    elif predicted_score >= BENCHMARK_2025["zhonggao_line"]:
        est = min(est, BENCHMARK_2025["zhonggao_count"])

    return max(1, min(THIRTEEN_SCHOOL["grade_2026"], est))


def compute_internal_ranking(academic_scores: dict, quality_score: float = 0) -> float:
    """
    十三中分配生综合得分:
    学业97% (初一20%+初二30%+初三50%) + 素质3%
    """
    weights = {
        "初一上": 0.10, "初一下": 0.10,
        "初二上": 0.15, "初二下": 0.15,
        "初三上": 0.25, "一模": 0.25,
    }
    academic = 0
    total_w = 0
    for key, w in weights.items():
        if key in academic_scores:
            academic += academic_scores[key] * w
            total_w += w

    if total_w > 0:
        academic = academic / total_w

    quality = min(quality_score, 10)
    return academic * 0.97 + quality * 0.03


def generate_quota_plans(student: Student) -> list[dict]:
    """生成 5 个分配生志愿方案"""
    rank = student.predicted_rank_school or 566

    plans = []
    for school in SCHOOLS_2026:
        if not school.rank_ref_2025:
            continue
        if school.quota_slots_2026 <= 0:
            continue

        if rank <= school.rank_ref_2025 * 0.7:
            tag = "🟢 稳"
            probability = "高 (>70%)"
        elif rank <= school.rank_ref_2025 * 1.1:
            tag = "🟡 冲"
            probability = "中 (40-70%)"
        elif rank <= school.rank_ref_2025 * 1.5:
            tag = "🔴 博"
            probability = "低 (15-40%)"
        else:
            continue

        plans.append({
            "学校": school.name,
            "类别": school.category,
            "分配名额": school.quota_slots_2026,
            "参考位次": f"前{school.rank_ref_2025}名(2025)",
            "策略": tag,
            "概率": probability,
            "备注": school.note,
            "rank_diff": school.rank_ref_2025 - rank,
        })

    # 排序：稳 → 冲 → 博
    def sort_key(p):
        order = {"🟢 稳": 0, "🟡 冲": 1, "🔴 博": 2}
        return (order.get(p["策略"], 9), -p["rank_diff"])

    plans.sort(key=sort_key)
    return plans[:5]


def generate_central_plans(student: Student) -> list[dict]:
    """生成 10 个集中招生第一批志愿方案"""
    rank = student.predicted_rank_school or 566
    city_pct = student.predicted_rank_city_pct or (rank / THIRTEEN_SCHOOL["grade_2026"] / 1.6)

    ALL_SCHOOLS = []
    for school in SCHOOLS_2026:
        rank_ref = school.rank_ref_2025 or 999
        city_score_line = school.rank_ref_2025 / THIRTEEN_SCHOOL["grade_2026"] / 1.6 if school.rank_ref_2025 else 0.5

        if city_pct < city_score_line * 0.7:
            tag, prob = "🟢 保", ">85%"
        elif city_pct < city_score_line * 1.0:
            tag, prob = "🟡 稳", "55-85%"
        elif city_pct < city_score_line * 1.3:
            tag, prob = "🟠 冲", "25-55%"
        else:
            continue

        ALL_SCHOOLS.append({
            "学校": school.name,
            "类别": school.category,
            "总计划": school.plan_total_2026,
            "策略": tag,
            "概率": prob,
            "备注": school.note,
            "score_line_rank": rank_ref,
        })

    ALL_SCHOOLS.sort(key=lambda s: (s["score_line_rank"], s["策略"]))
    return ALL_SCHOOLS[:10]
