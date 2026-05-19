"""配置管理"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    mail_smtp_server: str = "smtp.qq.com"
    mail_smtp_port: int = 465
    mail_user: str = ""
    mail_pass: str = ""
    mail_to_primary: str = ""
    mail_to_secondary: str = ""

    output_dir: str = "output"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            mail_smtp_server=os.getenv("MAIL_SMTP_SERVER", "smtp.qq.com"),
            mail_smtp_port=int(os.getenv("MAIL_SMTP_PORT", "465")),
            mail_user=os.getenv("MAIL_USER", ""),
            mail_pass=os.getenv("MAIL_PASS", ""),
            mail_to_primary=os.getenv("MAIL_TO_PRIMARY", ""),
            mail_to_secondary=os.getenv("MAIL_TO_SECONDARY", ""),
            output_dir=os.getenv("OUTPUT_DIR", "output"),
        )

    def is_valid(self) -> bool:
        if not self.deepseek_api_key:
            print("❌ 缺少 DEEPSEEK_API_KEY")
            return False
        if not self.mail_user or not self.mail_pass:
            print("❌ 缺少邮件配置")
            return False
        if not self.mail_to_primary:
            print("❌ 缺少 MAIL_TO_PRIMARY")
            return False
        return True
