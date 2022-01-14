import smtplib
from email.mime.text import MIMEText
from typing import Union, List

import config


def send_email(title: str, content: str, receivers: Union[List[str], str]) -> None:
    # 设置服务器所需信息
    host = config.mail_host
    port = config.mail_port
    user = config.mail_user
    password = config.mail_password
    sender = config.mail_sender

    # 设置email信息
    message = MIMEText(content, 'plain', 'utf-8')
    message['Subject'] = title
    message['From'] = sender
    message['To'] = ','.join(receivers) if isinstance(receivers, list) else receivers

    # 登录并发送邮件
    try:
        smtp = smtplib.SMTP_SSL(host, port)
        smtp.login(user, password)
        smtp.sendmail(sender, receivers, message.as_string())
        smtp.quit()
        print('邮件发送成功')
    except smtplib.SMTPException as e:
        print('邮件发送失败', e)  # 打印错误


if __name__ == '__main__':
    send_email('test', 'hi', [config.email])
