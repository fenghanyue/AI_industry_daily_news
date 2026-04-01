# -*- coding: utf-8 -*-
"""
邮件发送 - HTML 正文 + HTML 附件
"""

import os
import smtplib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)

SENDER_EMAIL    = os.environ.get("OUTLOOK_EMAIL", "")
SENDER_PASSWORD = os.environ.get("OUTLOOK_PASSWORD", "")
RECIPIENTS      = [r.strip() for r in os.environ.get("RECIPIENT_EMAILS", "").split(",") if r.strip()]
SMTP_HOST       = "smtp.163.com"
SMTP_PORT       = 465


def send_report(html_path: str):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        raise ValueError("OUTLOOK_EMAIL / OUTLOOK_PASSWORD 未设置")
    if not RECIPIENTS:
        raise ValueError("RECIPIENT_EMAILS 未设置")

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")
    subject   = f"AI 行业日报 · {yesterday}"

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 邮件正文用纯文本（兼容所有邮件客户端）
    plain_text = f"AI 行业日报 · {yesterday}\n\n请下载附件用浏览器打开查看完整日报。"

    msg = MIMEMultipart("mixed")
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = ", ".join(RECIPIENTS)
    msg["Subject"] = subject

    # 正文（纯文本 + HTML 两种格式，邮件客户端自动选择）
    body = MIMEMultipart("alternative")
    body.attach(MIMEText(plain_text, "plain", "utf-8"))
    body.attach(MIMEText(html_content, "html", "utf-8"))
    msg.attach(body)

    # 附件：同一个 HTML 文件
    filename = Path(html_path).name
    with open(html_path, "rb") as f:
        part = MIMEBase("text", "html")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    logger.info("发送邮件至: %s", RECIPIENTS)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())
    logger.info("邮件发送成功")
