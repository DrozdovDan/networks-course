import socket
import argparse
import sys


def send_command(host, port, command):
    """Отправляет команду на сервер и получает результат"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"[*] Подключение к {host}:{port}...")
        client.connect((host, port))
        print(f"[+] Соединение установлено")

        print(f"[*] Отправка команды: {command}")
        client.send(command.encode('utf-8'))

        response_size_str = client.recv(1024).decode('utf-8')

        try:
            response_size = int(response_size_str)

            client.send("ACK".encode('utf-8'))

            print(f"[*] Ожидание результата ({response_size} байт)...")

            result = ""
            bytes_received = 0

            while bytes_received < response_size:
                chunk = client.recv(min(response_size - bytes_received, 4096)).decode('utf-8')
                if not chunk:
                    break

                result += chunk
                bytes_received += len(chunk.encode('utf-8'))

            print("\n" + "=" * 50)
            print("РЕЗУЛЬТАТ ВЫПОЛНЕНИЯ КОМАНДЫ:")
            print("=" * 50)
            print(result)

        except ValueError:
            print(f"[!] Получен некорректный размер ответа: {response_size_str}")

    except Exception as e:
        print(f"[!] Ошибка: {str(e)}")
    finally:
        client.close()
        print("[-] Соединение закрыто")


def main():
    parser = argparse.ArgumentParser(description='Клиент для удаленного запуска команд')
    parser.add_argument('--host', required=True, help='IP-адрес сервера')
    parser.add_argument('--port', type=int, default=9999, help='Порт сервера (по умолчанию: 9999)')
    parser.add_argument('--command', '-c', help='Команда для выполнения')

    args = parser.parse_args()

    command = args.command
    if not command:
        command = input("Введите команду для выполнения: ")

    send_command(args.host, args.port, command)


if __name__ == "__main__":
    main()