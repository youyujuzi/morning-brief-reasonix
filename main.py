#!/usr/bin/env python3
"""
盘前作战地图 — 主入口

流程: 采集数据 → 统计建模 → AI生成早报 → 校验 → 发送
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from src.data import collect_all
from src.models import OpeningAnchorModel, EventMapper
from src.prompt import build_prompt, SYSTEM_PROMPT
from src.validator import validate_data, validate_report, should_send
from src.mailer import render_html, send_email

from openai import OpenAI


def generate_report(cfg: Config, prompt_text: str) -> str:
    """调用 DeepSeek API 生成早报"""
    print("\n🤖 调用 DeepSeek API...")
    try:
        client = OpenAI(api_key=cfg.deepseek_api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model=cfg.deepseek_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_text},
            ],
            temperature=0.5,
            max_tokens=4000,
        )
        content = response.choices[0].message.content
        if content:
            print(f"✅ 生成完成 ({len(content)} 字)")
            return content
        raise ValueError("返回内容为空")
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return ""


def main():
    print("=" * 50)
    print("📊 盘前作战地图 · 生成器")
    print("=" * 50)

    cfg = Config.from_env()
    if not cfg.is_valid():
        sys.exit(1)

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # 1. 采集数据
    data = collect_all(cfg)
    data["now"] = now

    # 2. 统计建模
    print("\n📈 开盘锚点建模...")
    reg_data = data.get("regression_data")
    if reg_data is not None and len(reg_data) >= 5:
        model = OpeningAnchorModel(reg_data)
        data["anchor_model"] = model
        print(model.summary())
    else:
        print("⚠️ 数据不足，跳过回归建模")

    # 3. 数据校验
    print("\n🔍 数据校验...")
    data_issues = validate_data(data)
    if data_issues:
        for issue in data_issues:
            print(f"   {issue}")

    # 4. 构建 Prompt
    print("\n📝 构建 Prompt...")
    prompt = build_prompt(data)

    # 5. AI 生成
    report = generate_report(cfg, prompt)
    if not report:
        print("❌ 早报生成失败，使用备用模板")
        report = "## 今日数据\n\n数据已采集，AI生成暂不可用。请查看网页版获取更多信息。"

    # 6. 早报校验
    print("\n🔍 早报校验...")
    report_issues = validate_report(report)
    if report_issues:
        for issue in report_issues:
            print(f"   {issue}")

    # 7. 判断是否发送
    print("\n📋 发送决策...")
    ok, reason = should_send(data_issues, report_issues)
    print(f"   {reason}")
    if not ok:
        print("❌ 早报被拦截，未发送")
        # 即使不发送，也保存到本地
        html = render_html(report, date_str)
        os.makedirs(cfg.output_dir, exist_ok=True)
        with open(f"{cfg.output_dir}/intercepted_{date_str}.html", "w", encoding="utf-8") as f:
            f.write(html)
        return

    # 8. 渲染 + 保存
    print("\n💾 保存文件...")
    html = render_html(report, date_str)
    os.makedirs(f"{cfg.output_dir}/archive", exist_ok=True)
    
    with open(f"{cfg.output_dir}/archive/{date_str}.md", "w", encoding="utf-8") as f:
        f.write(report)
    with open(f"{cfg.output_dir}/archive/{date_str}.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open(f"{cfg.output_dir}/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open(f"{cfg.output_dir}/latest.md", "w", encoding="utf-8") as f:
        f.write(report)

    # 9. 发送
    send_email(cfg, html, date_str)

    # 10. 总结
    print("\n" + "=" * 50)
    print("✅ 执行完毕")
    print("=" * 50)


if __name__ == "__main__":
    main()
