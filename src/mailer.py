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
<style>
  body { font-family: -apple-system, "Noto Sans SC", sans-serif; background: #f5f5f7; color: #1a1a2e; padding: 20px; line-height: 1.7; }
  .container { max-width: 700px; margin: 0 auto; }
  .header { background: #1e3a5f; color: #fff; border-radius: 12px; padding: 28px 24px; margin-bottom: 16px; }
  .header h1 { margin: 0 0 4px 0; font-size: 22px; }
  .header .sub { opacity: 0.8; font-size: 13px; }
  .header .badge { display: inline-block; background: rgba(255,255,255,0.15); padding: 3px 10px; border-radius: 12px; font-size: 11px; margin-top: 8px; }
  .card { background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 12px; border: 1px solid #e5e7eb; }
  .card h2 { font-size: 19px; margin: 0 0 12px 0; padding-bottom: 8px; border-bottom: 3px solid #2563eb; color: #1a1a2e; }
  .card h3 { font-size: 16px; margin: 18px 0 8px; color: #1a1a2e; }
  .card h4 { font-size: 15px; margin: 12px 0 6px; }
  .card p { margin: 0 0 8px; color: #555; font-size: 14px; }
  .card table { width: 100%; border-collapse: collapse; margin: 10px 0 14px; font-size: 13px; border: 1px solid #e5e7eb; }
  .card table thead { background: #1e3a5f; }
  .card table th { padding: 8px 10px; text-align: left; font-weight: 600; color: #fff; border: 1px solid #1e3a5f; }
  .card table td { padding: 6px 10px; border: 1px solid #e5e7eb; color: #1a1a2e; }
  .card table tbody tr:nth-child(even) { background: #f8f9fa; }
  .card a { color: #2563eb; }
  .card blockquote { border-left: 4px solid #dbeafe; padding: 8px 16px; margin: 8px 0; background: #f8faff; border-radius: 0 6px 6px 0; font-size: 13px; color: #333; }
  .green { color: #16a34a; font-weight: 500; }
  .red { color: #dc2626; font-weight: 500; }
  .footer { text-align: center; padding: 16px; color: #999; font-size: 12px; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>盘前作战地图</h1>
    <div class="sub">{date}</div>
    <div class="badge">AI生成 · 仅供参考 · 不构成投资建议</div>
  </div>
  <div class="card">{content}</div>
  <div class="footer">
    <p>每日盘前自动发送 · 🌐 <a href="https://youyujuzi.github.io/morning-brief/">网页版</a></p>
  </div>
</div>
</body>
</html>"""


def render_html(markdown_text: str, date: str) -> str:
    """Markdown → HTML"""
    html_body = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
    # 用 replace 代替 format，避免 CSS 花括号冲突
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
            f"🌐 网页版: https://youyujuzi.github.io/morning-brief/",
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
