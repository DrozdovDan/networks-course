import socket
import ssl
import base64
import argparse
import sys
import time
from getpass import getpass


def send_command(sock, command, expected_code):
    """Отправляет команду на сервер и проверяет код ответа"""
    print(f">> {command}")
    sock.send((command + '\r\n').encode())

    response = sock.recv(1024).decode()
    print(f"<< {response}")

    response_code = response[:3]
    if response_code != expected_code:
        raise Exception(f"Ожидался код {expected_code}, получен: {response}")

    return response


def send_email_via_socket(server, port, sender, recipient, subject, message, use_tls=True, username=None,
                          password=None):
    """Отправляет email через SMTP используя сокеты напрямую"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"Соединение с {server}:{port}...")
        sock.connect((server, port))

        greeting = sock.recv(1024).decode()
        print(f"<< {greeting}")

        if not greeting.startswith('220'):
            raise Exception(f"Неожиданный ответ от сервера: {greeting}")

        domain = sender.split('@')[1]
        send_command(sock, f"EHLO {domain}", "250")

        if use_tls:
            send_command(sock, "STARTTLS", "220")

            context = ssl.create_default_context()
            secure_sock = context.wrap_socket(sock, server_hostname=server)
            sock = secure_sock

            send_command(sock, f"EHLO {domain}", "250")

        if username and password:
            send_command(sock, "AUTH LOGIN", "334")

            username_b64 = base64.b64encode(username.encode()).decode()
            send_command(sock, username_b64, "334")

            password_b64 = base64.b64encode(password.encode()).decode()
            send_command(sock, password_b64, "235")

        send_command(sock, f"MAIL FROM:<{sender}>", "250")

        send_command(sock, f"RCPT TO:<{recipient}>", "250")

        send_command(sock, "DATA", "354")

        date = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        email_content = f"From: {sender}\r\n"
        email_content += f"To: {recipient}\r\n"
        email_content += f"Subject: {subject}\r\n"
        email_content += f"Date: {date}\r\n"
        email_content += f"Content-Type: text/plain; charset=utf-8\r\n"
        email_content += "\r\n"
        email_content += message
        email_content += "\r\n.\r\n"

        print(f">> [Отправка содержимого письма]")
        sock.send(email_content.encode())

        response = sock.recv(1024).decode()
        print(f"<< {response}")

        if not response.startswith('250'):
            raise Exception(f"Ошибка при отправке данных: {response}")

        send_command(sock, "QUIT", "221")

        print("Сообщение успешно отправлено!")
        return True

    except Exception as e:
        print(f"Ошибка при отправке почты: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description='SMTP-клиент на сокетах')
    parser.add_argument('--server', '-s', required=True, help='SMTP сервер')
    parser.add_argument('--port', '-p', type=int, default=587, help='Порт сервера (по умолчанию 587)')
    parser.add_argument('--sender', '-f', required=True, help='Email отправителя')
    parser.add_argument('--recipient', '-r', required=True, help='Email получателя')
    parser.add_argument('--subject', '-j', default='Тестовое сообщение', help='Тема сообщения')
    parser.add_argument('--message', '-m', help='Текст сообщения')
    parser.add_argument('--no-tls', action='store_true', help='Отключить использование TLS')
    parser.add_argument('--username', '-u', help='Имя пользователя для авторизации')

    args = parser.parse_args()

    password = None
    if args.username:
        password = getpass("Введите пароль: ")

    if args.message:
        message = args.message
    else:
        message = """
Привет!

Это тестовое сообщение в формате TXT.
Проверка отправки почты с помощью сокетов Python.

С уважением,
Почтовый клиент Python
"""

    send_email_via_socket(
        args.server,
        args.port,
        args.sender,
        args.recipient,
        args.subject,
        message,
        use_tls=not args.no_tls,
        username=args.username,
        password=password
    )


if __name__ == "__main__":
    main()