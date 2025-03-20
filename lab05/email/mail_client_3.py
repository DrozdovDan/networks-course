import socket
import ssl
import base64
import argparse
import sys
import time
import os
import uuid
from getpass import getpass
from email.utils import formatdate


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


def generate_boundary():
    """Создает уникальный разделитель для MIME частей"""
    return f"------------{uuid.uuid4().hex}"


def encode_image_base64(image_path):
    """Кодирует изображение в Base64"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            return base64.b64encode(image_data).decode()
    except Exception as e:
        print(f"Ошибка при чтении файла {image_path}: {e}")
        sys.exit(1)


def get_content_type(filename):
    """Определяет MIME тип файла по расширению"""
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.jpg' or ext == '.jpeg':
        return 'image/jpeg'
    elif ext == '.png':
        return 'image/png'
    elif ext == '.gif':
        return 'image/gif'
    else:
        return 'application/octet-stream'


def create_mime_message(sender, recipient, subject, text_message, image_path=None):
    """Создает MIME сообщение с текстом и изображением"""
    boundary = generate_boundary()

    headers = f"From: {sender}\r\n"
    headers += f"To: {recipient}\r\n"
    headers += f"Subject: {subject}\r\n"
    headers += f"Date: {formatdate(localtime=True)}\r\n"
    headers += f"MIME-Version: 1.0\r\n"

    if image_path:
        headers += f"Content-Type: multipart/mixed; boundary=\"{boundary}\"\r\n"
        headers += "\r\n"

        message = f"--{boundary}\r\n"
        message += "Content-Type: text/plain; charset=utf-8\r\n"
        message += "Content-Transfer-Encoding: 7bit\r\n"
        message += "\r\n"
        message += text_message
        message += "\r\n"

        if image_path:
            image_filename = os.path.basename(image_path)
            content_type = get_content_type(image_filename)
            image_data = encode_image_base64(image_path)

            message += f"--{boundary}\r\n"
            message += f"Content-Type: {content_type}\r\n"
            message += f"Content-Transfer-Encoding: base64\r\n"
            message += f"Content-Disposition: attachment; filename=\"{image_filename}\"\r\n"
            message += "\r\n"

            for i in range(0, len(image_data), 76):
                message += image_data[i:i + 76] + "\r\n"

        message += f"--{boundary}--\r\n"
    else:
        headers += "Content-Type: text/plain; charset=utf-8\r\n"
        headers += "\r\n"
        message = text_message

    return headers + message


def send_email_via_socket(server, port, sender, recipient, subject, message, image_path=None, use_tls=True,
                          username=None, password=None):
    """Отправляет email через SMTP используя сокеты напрямую"""
    # Создаем TCP сокет
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

        email_content = create_mime_message(sender, recipient, subject, message, image_path)

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
    parser = argparse.ArgumentParser(description='SMTP-клиент с поддержкой вложений')
    parser.add_argument('--server', '-s', required=True, help='SMTP сервер')
    parser.add_argument('--port', '-p', type=int, default=587, help='Порт сервера (по умолчанию 587)')
    parser.add_argument('--sender', '-f', required=True, help='Email отправителя')
    parser.add_argument('--recipient', '-r', required=True, help='Email получателя')
    parser.add_argument('--subject', '-j', default='Тестовое сообщение с изображением', help='Тема сообщения')
    parser.add_argument('--message', '-m', help='Текст сообщения')
    parser.add_argument('--image', '-i', help='Путь к изображению для вложения')
    parser.add_argument('--no-tls', action='store_true', help='Отключить использование TLS')
    parser.add_argument('--username', '-u', help='Имя пользователя для авторизации')

    args = parser.parse_args()

    if args.image and not os.path.exists(args.image):
        print(f"Ошибка: файл {args.image} не найден")
        sys.exit(1)

    password = None
    if args.username:
        password = getpass("Введите пароль: ")

    if args.message:
        message = args.message
    else:
        message = """
Привет!

Это тестовое сообщение с прикрепленным изображением.
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
        image_path=args.image,
        use_tls=not args.no_tls,
        username=args.username,
        password=password
    )


if __name__ == "__main__":
    main()