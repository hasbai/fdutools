import smtplib
from email.mime.text import MIMEText
import config


def send_email(title, content):
    # 设置服务器所需信息
    host = config.mail_host
    port = config.mail_port
    user = config.mail_user
    password = config.mail_password
    sender = config.mail_sender
    receivers = config.mail_receiver

    # 设置email信息
    message = MIMEText(content, 'plain', 'utf-8')
    message['Subject'] = title
    message['From'] = sender
    message['To'] = receivers

    # 登录并发送邮件
    try:
        smtp = smtplib.SMTP_SSL(host, port)
        smtp.login(user, password)
        smtp.sendmail(sender, receivers, message.as_string())
        smtp.quit()
        print('邮件发送成功')
    except smtplib.SMTPException as e:
        print('邮件发送失败', e)  # 打印错误
