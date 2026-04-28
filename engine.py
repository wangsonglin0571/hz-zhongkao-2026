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

    def predict(self) -> dict:
        """基于历史成绩回归预测中考分数和排名"""
        if len(self.exams) < 2:
            return {"error": "至少需要2次考试成绩"}

        # 简单线性回归：用考试顺序编号 → 分数百分比
        names = list(self.exams.keys())
        xs = list(range(len(names)))
        ys = [self.exams[n]["pct"] for n in names]

        n = len(xs)
        sum_x, sum_y = sum(xs), sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        sum_x2 = sum(x * x for x in xs)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        # 预测下一次考试（中考）的百分比
        next_x = len(names)
        predicted_pct = intercept + slope * next_x

        # 置信区间
        residuals = [ys[i] - (intercept + slope * xs[i]) for i in range(n)]
        rmse = math.sqrt(sum(r * r for r in residuals) / n) if n > 1 else 0.02
        ci_low = max(0.3, predicted_pct - 2 * rmse)
        ci_high = min(0.99, predicted_pct + 2 * rmse)

        predicted_score = predicted_pct * 650

        # 校内排名预测：基于最后一次考试的排名趋势
        ranks = [self.exams[n]["rank"] for n in names]
        rank_slope = 0
        if len(ranks) >= 2:
            rank_diffs = [ranks[i] - ranks[i+1] for i in range(len(ranks)-1)]
            rank_slope = sum(rank_diffs) / len(rank_diffs)

        last_rank = ranks[-1]
        predicted_rank = max(1, int(last_rank + rank_slope * 0.5))

        # 全市排名估算（十三中学生实际水平高于全市平均）
        # 十三中重高率28.64%，全市重高率约17.8%
        city_advantage = THIRTEEN_SCHOOL["zhonggao_rate"] / 0.178
        predicted_rank_city_pct = (predicted_rank / self.grade_size) / city_advantage

        self.predicted_score = predicted_score
        self.predicted_rank_school = predicted_rank
        self.predicted_rank_city_pct = predicted_rank_city_pct

        return {
            "趋势": "上升" if slope > 0 else "下降" if slope < 0 else "稳定",
            "预测得分": round(predicted_score, 1),
            "置信区间": f"{round(ci_low * 650)} - {round(ci_high * 650)}",
            "预测校内排名": predicted_rank,
            "估测全市排名百分比": f"{predicted_rank_city_pct*100:.1f}%",
        }


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
