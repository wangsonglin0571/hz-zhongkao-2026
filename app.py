#!/usr/bin/env python3
"""
杭州2026中考志愿填报 — 交互式入口
"""

import json
from engine import Student, generate_quota_plans, generate_central_plans, POLICY_2026, THIRTEEN_SCHOOL, SCHOOLS_2026


def cli():
    print("╔══════════════════════════════════╗")
    print("║  杭州2026中考志愿填报 · 十三中版  ║")
    print("╚══════════════════════════════════╝")
    print(f"\n📊 {THIRTEEN_SCHOOL['name']} - 本届 {THIRTEEN_SCHOOL['grade_2026']} 人")
    print(f"📋 2026 分配生总名额: {POLICY_2026['city_quota_total']} | 十三中预估: {THIRTEEN_SCHOOL['quota_2026_est']}\n")

    student = Student(grade_size=THIRTEEN_SCHOOL["grade_2026"])

    # ── 输入成绩 ──
    exams_config = [
        ("九上期末", None),
        ("一模", None),
        ("二模", None),
        ("三模", None),
    ]

    for name, _ in exams_config:
        try:
            s = input(f"{name} 成绩 (得分/总分/校排, 如 510/620/320, 跳过回车): ").strip()
            if not s:
                continue
            parts = s.split("/")
            score, total, rank = float(parts[0]), int(parts[1]), int(parts[2])
            student.add_exam(name, score, total, rank)
        except (ValueError, IndexError):
            pass

    if len(student.exams) < 2:
        print(f"\n⚠️ 成绩不足，使用预设示例数据演示")
        student.add_exam("九上期末", 520, 620, 310)
        student.add_exam("一模", 535, 620, 285)
        student.add_exam("二模", 548, 620, 260)

    # ── 预测 ──
    print("\n" + "=" * 50)
    print("🔮 成绩预测")
    print("=" * 50)

    pred = student.predict()
    for k, v in pred.items():
        print(f"  {k}: {v}")

    # ── 分配生方案 ──
    print("\n" + "=" * 50)
    print(f"🎯 分配生志愿方案 (最多 {POLICY_2026['quota_max_schools']} 个)")
    print("=" * 50)

    quota_plans = generate_quota_plans(student)
    for i, p in enumerate(quota_plans, 1):
        print(f"\n  [{i}] {p['策略']} {p['学校']}")
        print(f"      分配名额: {p['分配名额']} | 参考位次: {p['参考位次']}")
        print(f"      概率: {p['概率']} | {p['备注']}")

    # ── 集中招生方案 ──
    print("\n" + "=" * 50)
    print(f"📝 集中招生第一批志愿方案 (最多 {POLICY_2026['central_first_max_schools']} 个)")
    print("=" * 50)

    central_plans = generate_central_plans(student)
    for i, p in enumerate(central_plans, 1):
        print(f"\n  [{i}] {p['策略']} {p['学校']}")
        print(f"      招生计划: {p['总计划']} | 概率: {p['概率']} | {p['备注']}")

    # ── 关键提醒 ──
    print("\n" + "=" * 50)
    print("⚠️ 关键提醒")
    print("=" * 50)
    print(f"""
  1. 填报时间: {POLICY_2026['quota_apply_date'][0]} ~ {POLICY_2026['quota_apply_date'][1]}
  2. 填报入口: {POLICY_2026['system_url']}
  3. 填报后不可修改！提前规划
  4. 分配生需综评3A + 连续三年在读
  5. 同分排序: 语文数学 → 英语 → 科学 → 社会
  6. 5月初关注学校公示的正式分配方案
    """)

    # ── 导出 ──
    output = {
        "预测": pred,
        "分配生方案": [{"排名": i+1, **p} for i, p in enumerate(quota_plans)],
        "集中招生第一段": [{"排名": i+1, **p} for i, p in enumerate(central_plans)],
    }
    path = Path(__file__).parent / "plans_output.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📁 方案已导出: {path}")


if __name__ == "__main__":
    cli()
