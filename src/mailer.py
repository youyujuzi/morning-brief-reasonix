"""
邮件发送模块 — 双邮箱发送 + HTML渲染
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr

import markdown

from config import Config


HTML_WRAPPER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f5f5f7;font-family:-apple-system,'Noto Sans SC',sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f7;">
<tr><td align="center" style="padding:16px 10px;">
<table role="presentation" width="100%" style="max-width:640px;background:#ffffff;border-radius:10px;border:1px solid #e5e7eb;">
<tr><td style="background:#1e3a5f;padding:22px 20px;border-radius:10px 10px 0 0;">
  <h1 style="margin:0 0 2px;font-size:20px;color:#ffffff;">盘前作战地图</h1>
  <p style="margin:0;font-size:12px;color:rgba(255,255,255,0.8);">{date}</p>
  <p style="margin:6px 0 0;font-size:11px;color:rgba(255,255,255,0.6);display:inline-block;background:rgba(255,255,255,0.12);padding:2px 10px;border-radius:10px;">AI生成 · 仅供参考</p>
</td></tr>
<tr><td style="padding:20px;font-size:14px;line-height:1.7;color:#1a1a2e;">
{content}
</td></tr>
<tr><td style="text-align:center;padding:12px 20px;font-size:11px;color:#999;border-top:1px solid #eee;">
<p style="margin:0;">每日盘前自动发送 · <a href="https://youyujuzi.github.io/morning-brief-reasonix/" style="color:#2563eb;">网页版</a></p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _style_table(html: str) -> str:
    """给表格加上内联样式，兼容QQ邮箱"""
    import re
    # 给 <table> 加样式
    html = re.sub(r'<table>', '<table style="width:100%;border-collapse:collapse;margin:8px 0 14px;font-size:13px;border:1px solid #d0d0d0;">', html)
    # 给 <thead> 加背景
    html = re.sub(r'<thead>', '<thead style="background:#1e3a5f;color:#ffffff;">', html)
    # 给 <th> 加样式
    html = re.sub(r'<th>', '<th style="padding:7px 10px;text-align:left;font-weight:600;border:1px solid #1e3a5f;color:#ffffff;">', html)
    # 给 <td> 加样式
    html = re.sub(r'<td>', '<td style="padding:6px 10px;border:1px solid #d0d0d0;color:#1a1a2e;">', html)
    # 给 <tr> 隔行变色
    html = re.sub(r'<tr>', '<tr style="background:#ffffff;">', html)
    # <blockquote> 加样式
    html = re.sub(r'<blockquote>', '<blockquote style="border-left:4px solid #dbeafe;padding:8px 16px;margin:8px 0;background:#f8faff;color:#333;font-size:13px;">', html)
    # <h2> 加样式
    html = re.sub(r'<h2>', '<h2 style="font-size:18px;margin:16px 0 10px;padding-bottom:6px;border-bottom:3px solid #2563eb;color:#1a1a2e;">', html)
    # <h3> 加样式
    html = re.sub(r'<h3>', '<h3 style="font-size:15px;margin:14px 0 6px;color:#1a1a2e;">', html)
    # <p> 加样式
    html = re.sub(r'<p>', '<p style="margin:0 0 6px;color:#555;font-size:14px;line-height:1.6;">', html)
    return html


def render_html(markdown_text: str, date: str) -> str:
    """Markdown → HTML"""
    html_body = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
    html_body = _style_table(html_body)
    html = HTML_WRAPPER.replace("{date}", date).replace("{content}", html_body)
    return html


def send_email(cfg: Config, html_content: str, date: str) -> bool:
    """发送邮件到主邮箱和副邮箱"""
    print(f"\n📧 发送邮件...")
    
    recipients = [cfg.mail_to_primary]
    if cfg.mail_to_secondary:
        recipients.append(cfg.mail_to_secondary)
        print(f"   → 主: {cfg.mail_to_primary}")
        print(f"   → 副: {cfg.mail_to_secondary}")
    else:
        print(f"   → {cfg.mail_to_primary}")

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr(("盘前作战地图", cfg.mail_user))
        msg["Subject"] = Header(f"📊 盘前作战地图 · {date}", "utf-8")

        text_part = MIMEText(
            f"盘前作战地图 · {date}\n\n请查看HTML版本以获取完整格式。\n\n"
            f"🌐 网页版: https://youyujuzi.github.io/morning-brief-reasonix/",
            "plain", "utf-8"
        )
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(text_part)
        msg.attach(html_part)

        if cfg.mail_smtp_port == 465:
            with smtplib.SMTP_SSL(cfg.mail_smtp_server, cfg.mail_smtp_port, timeout=30) as server:
                server.login(cfg.mail_user, cfg.mail_pass)
                server.sendmail(cfg.mail_user, recipients, msg.as_string())
        else:
            with smtplib.SMTP(cfg.mail_smtp_server, cfg.mail_smtp_port, timeout=30) as server:
                server.starttls()
                server.login(cfg.mail_user, cfg.mail_pass)
                server.sendmail(cfg.mail_user, recipients, msg.as_string())

        print("✅ 邮件发送成功")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False
