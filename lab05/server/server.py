import socket
import subprocess
import threading
import argparse
import sys
import os


def execute_command(command):
    """Выполняет команду и возвращает её вывод"""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        return_code = process.returncode

        result = f"=== ВЫПОЛНЕНИЕ КОМАНДЫ: {command} ===\n"
        result += f"Код возврата: {return_code}\n\n"

        if stdout:
            result += f"=== СТАНДАРТНЫЙ ВЫВОД ===\n{stdout}\n"

        if stderr:
            result += f"=== ОШИБКИ ===\n{stderr}\n"

        return result
    except Exception as e:
        return f"Ошибка при выполнении команды: {str(e)}"


def handle_client(client_socket, address):
    """Обрабатывает подключение клиента"""
    print(f"[+] Установлено соединение с {address[0]}:{address[1]}")

    try:
        command = client_socket.recv(1024).decode('utf-8').strip()
        print(f"[*] Получена команда: {command}")

        if not command:
            client_socket.send("Команда не получена".encode('utf-8'))
            return

        result = execute_command(command)
        print(f"[*] Команда выполнена. Отправка результата...")

        result_size = len(result.encode('utf-8'))
        client_socket.send(str(result_size).encode('utf-8'))

        ack = client_socket.recv(1024).decode('utf-8')

        client_socket.send(result.encode('utf-8'))

        print(f"[+] Результат отправлен клиенту.")

    except Exception as e:
        print(f"[!] Ошибка при обработке запроса: {str(e)}")
    finally:
        client_socket.close()
        print(f"[-] Соединение с {address[0]}:{address[1]} закрыто")


def start_server(host, port, max_connections=5):
    """Запускает сервер для прослушивания входящих соединений"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        server.bind((host, port))

        server.listen(max_connections)
        print(f"[+] Сервер запущен на {host}:{port}")

        while True:
            client_socket, address = server.accept()

            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, address)
            )
            client_thread.daemon = True
            client_thread.start()

    except KeyboardInterrupt:
        print("\n[!] Завершение работы сервера...")
    except Exception as e:
        print(f"[!] Ошибка сервера: {str(e)}")
    finally:
        server.close()
        print("[+] Сервер остановлен")


def main():
    parser = argparse.ArgumentParser(description='Сервер для удаленного запуска команд')
    parser.add_argument('--host', default='127.0.0.1', help='IP-адрес для прослушивания (по умолчанию: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=9999, help='Порт для прослушивания (по умолчанию: 9999)')

    args = parser.parse_args()

    start_server(args.host, args.port)


if __name__ == "__main__":
    main()