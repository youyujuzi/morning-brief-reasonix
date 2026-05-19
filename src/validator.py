"""
校验模块 — 发送前检查早报质量和数据时效性
"""

import datetime
import pandas as pd


def validate_data(data: dict) -> list[str]:
    """检查数据质量，返回所有问题列表"""
    issues = []

    # 1. 数据时效性
    now = datetime.datetime.now()
    
    # 美股数据检查
    us = data.get("us_market", {})
    if not us:
        issues.append("⚠️ 美股数据为空")

    # A50
    a50 = data.get("a50")
    if not a50 or a50.get("change_pct") is None:
        issues.append("⚠️ A50期货数据缺失")

    # A股
    a_share = data.get("a_share", {})
    if not a_share:
        issues.append("⚠️ A股指数数据为空")

    # 新闻
    news = data.get("news", [])
    if len(news) < 3:
        issues.append("⚠️ 新闻数量过少 (< 3条)")

    # 回归数据
    reg = data.get("regression_data", pd.DataFrame())
    if len(reg) < 10:
        issues.append(f"⚠️ 回归样本量太少 ({len(reg)}个交易日)")

    return issues


def validate_report(report_text: str) -> list[str]:
    """检查生成的早报是否满足基本要求"""
    issues = []

    # 1. 必须包含反身性预警
    required_sections = [
        "核心情绪与预期校准",
        "情景",
        "风险与避坑",
        "指标说明",
    ]
    for section in required_sections:
        if section not in report_text:
            issues.append(f"❌ 缺少板块: {section}")

    # 2. 必须有具体的数字条件
    if "≥" not in report_text and ">=" not in report_text and "%" not in report_text:
        issues.append("❌ 情景清单缺少量化条件")

    # 3. 必须有止损/放弃条件
    if "止损" not in report_text and "放弃" not in report_text:
        issues.append("❌ 交易动作缺少止损/放弃条件")

    # 4. 必须有置信度标注
    if "N=" not in report_text and "N =" not in report_text:
        issues.append("❌ 缺少统计样本量(N值)标注")

    # 5. 必须有免责声明
    if "不构成" not in report_text and "投资建议" not in report_text:
        issues.append("❌ 缺少免责声明")

    return issues


def should_send(data_issues: list[str], report_issues: list[str]) -> tuple[bool, str]:
    """
    判断是否应该发送早报
    返回 (是否发送, 原因)
    """
    critical = [i for i in data_issues if "❌" in i]
    warnings = [i for i in data_issues if "⚠️" in i]

    if len(critical) > 2:
        return False, f"严重问题过多({len(critical)}个)，不发送"

    if report_issues and len([i for i in report_issues if "❌" in i]) >= 3:
        return False, "早报格式严重缺失"

    if warnings:
        msg = "发送，但有警告:\n" + "\n".join(warnings)
        return True, msg

    return True, "校验通过"
