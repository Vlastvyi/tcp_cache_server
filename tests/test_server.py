# tests/test_server.py
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server.py"

def pick_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port

def wait_port(host: str, port: int, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), 0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Server did not start on {host}:{port} within {timeout}s")

def send_command(cmd: str, host: str, port: int) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall((cmd.rstrip() + "\n").encode())
        return s.recv(4096).decode().strip()

class ServerProc:
    def __init__(self, host="127.0.0.1", port=None):
        self.host = host
        self.port = port or pick_free_port()
        self.p = None

    def __enter__(self):
        self.p = subprocess.Popen(
            [sys.executable, str(SERVER), "--host", self.host, "--port", str(self.port)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        wait_port(self.host, self.port)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.p and self.p.poll() is None:
            self.p.terminate()
            try:
                self.p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.p.kill()

def test_set_get_basic():
    with ServerProc() as sp:
        assert send_command("SET a 1", sp.host, sp.port) == "OK"
        assert send_command("GET a", sp.host, sp.port) == "1"
        assert send_command("GET missing", sp.host, sp.port) == "(nil)"

def test_set_overwrite_and_spaces():
    with ServerProc() as sp:
        assert send_command("SET key val", sp.host, sp.port) == "OK"
        # множественные пробелы между аргументами
        assert send_command("SET   key   new", sp.host, sp.port) == "OK"
        assert send_command("GET key", sp.host, sp.port) == "new"

def test_ttl_expires():
    with ServerProc() as sp:
        assert send_command("SET t v EX 1", sp.host, sp.port) == "OK"
        assert send_command("GET t", sp.host, sp.port) == "v"
        time.sleep(1.4)
        assert send_command("GET t", sp.host, sp.port) == "(nil)"

def test_zero_ttl():
    with ServerProc() as sp:
        assert send_command("SET k v EX 0", sp.host, sp.port) == "OK"
        # даём планировщику шанс тикнуть
        time.sleep(0.05)
        assert send_command("GET k", sp.host, sp.port) == "(nil)"

def test_invalid_commands():
    with ServerProc() as sp:
        assert send_command("GET", sp.host, sp.port).startswith("ERR")
        assert send_command("SET only_key", sp.host, sp.port).startswith("ERR")
        assert send_command("SET a b EX -5", sp.host, sp.port).startswith("ERR")
        assert send_command("SET a b EX notint", sp.host, sp.port).startswith("ERR")
        assert send_command("UNKNOWN x", sp.host, sp.port) == "ERR Unknown command"
