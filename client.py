# client.py
import socket
import time

HOST = "127.0.0.1"
PORT = 6379

def send_command(command: str) -> str:
    """Отправляем команду серверу и возвращаем ответ"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall((command + "\n").encode())
        data = s.recv(4096)
    return data.decode().strip()


if __name__ == "__main__":
    # Проверка SET и GET
    print(send_command("SET foo bar"))    # должно вернуть OK
    print(send_command("GET foo"))        # должно вернуть bar

    # Проверка TTL (ключ живёт 2 секунды)
    print(send_command("SET temp 123 EX 2"))  # OK
    print(send_command("GET temp"))           # 123
    print("Ждём 3 секунды...")
    time.sleep(3)
    print(send_command("GET temp"))           # (nil)

    # Проверка некорректных команд
    print(send_command("SET only_one_arg"))   # ERR
    print(send_command("GET"))                # ERR
