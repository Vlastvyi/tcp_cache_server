# client.py
import socket

HOST = "127.0.0.1"
PORT = 6379

def send_command(command: str, host=HOST, port=PORT) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall((command.rstrip() + "\n").encode())
        data = s.recv(4096)
        return data.decode().strip()

if __name__ == "__main__":
    print(send_command("SET foo bar"))
    print(send_command("GET foo"))
    print(send_command("SET temp value EX 2"))
    print(send_command("GET temp"))
