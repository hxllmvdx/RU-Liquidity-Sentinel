import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_mail(
        recipient_mail: str,
        color: str,
        point: str
):
    """Отправка письма на указанный email"""
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    sender_mail = "matmodtest@gmail.com"
    sender_password = "hzto agrz hcan iwgv"
    body = f"""
    Уровень ликвидности: {color}

    Значение стресса: {point}
    """
    msg = MIMEMultipart()
    msg["From"] = sender_mail
    msg["To"] = recipient_mail
    msg["Subject"] = f'{color} уровень ликвидности'
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_mail, sender_password)
        server.sendmail(sender_mail, recipient_mail, msg.as_string())
        server.quit()

    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")