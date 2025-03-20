import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import sys


def send_email(recipient, subject, message, format_type):
    smtp_server = 'smtp.rambler.ru'
    smtp_port = 587
    sender_email = 'matvei.isupov.education@rambler.ru' # 'drozd0ff-d4ny@rambler.ru' - не хочет подключаться почему-то
    password = '***************'

    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject

    if format_type.lower() == 'txt':
        msg.attach(MIMEText(message, 'plain'))
        print(f"Отправка текстового сообщения для {recipient}...")
    elif format_type.lower() == 'html':
        msg.attach(MIMEText(message, 'html'))
        print(f"Отправка HTML сообщения для {recipient}...")
    else:
        print(f"Неподдерживаемый формат: {format_type}")
        sys.exit(1)

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=5) as server:
            server.set_debuglevel(1)
            server.ehlo()
            server.starttls()

            server.login(sender_email, password)

            server.send_message(msg)
            server.quit()

        print(f"Сообщение успешно отправлено!")
        return True
    except Exception as e:
        print(f"Ошибка при отправке почты: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Отправка электронной почты')
    parser.add_argument('recipient', help='Адрес электронной почты получателя')
    parser.add_argument('--subject', '-s', default='Тестовое сообщение', help='Тема сообщения')
    parser.add_argument('--format', '-f', choices=['txt', 'html'], default='txt',
                        help='Формат сообщения (txt или html)')
    parser.add_argument('--message', '-m', help='Текст сообщения')

    args = parser.parse_args()

    if args.message:
        message = args.message
    else:
        if args.format.lower() == 'txt':
            message = """
Привет!

Это тестовое сообщение в формате TXT.
Проверка отправки почты с помощью Python.

С уважением,
Почтовый клиент Python
"""
        else:
            message = """
<html>
<head>
    <style>
        body {font-family: Arial, sans-serif;}
        .header {color: #4285f4; font-size: 24px;}
        .content {margin: 20px 0; line-height: 1.5;}
        .footer {color: #666; font-size: 14px;}
    </style>
</head>
<body>
    <div class="header">Привет!</div>
    <div class="content">
        <p>Это тестовое сообщение в формате <strong>HTML</strong>.</p>
        <p>Проверка отправки почты с помощью Python.</p>
    </div>
    <div class="footer">С уважением,<br>Почтовый клиент Python</div>
</body>
</html>
"""

    send_email(args.recipient, args.subject, message, args.format)


if __name__ == "__main__":
    main()