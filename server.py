# server.py
import argparse
import socket
import threading
import time
from typing import Dict, Optional, Tuple

ValueRecord = Tuple[str, Optional[float]]  # (value, expire_ts)
data_store: Dict[str, ValueRecord] = {}
lock = threading.RLock()


def cmd_set(args):
    if len(args) < 2:
        return "ERR Wrong number of arguments for SET"
    key, value = args[0], args[1]
    expire_time = None

    # Optional: EX seconds
    if len(args) == 4 and args[2].upper() == "EX":
        try:
            ttl_sec = int(args[3])
            if ttl_sec < 0:
                return "ERR Invalid expire time"
            expire_time = time.time() + ttl_sec
        except ValueError:
            return "ERR Invalid expire time"
    elif len(args) not in (2, 4):
        return "ERR Wrong number of arguments for SET"

    with lock:
        data_store[key] = (value, expire_time)
    return "OK"


def cmd_get(args):
    if len(args) != 1:
        return "ERR Wrong number of arguments for GET"
    key = args[0]

    with lock:
        rec = data_store.get(key)
        if rec is None:
            return "(nil)"
        value, expire_ts = rec
        if expire_ts is not None and time.time() > expire_ts:
            # lazy delete on read
            del data_store[key]
            return "(nil)"
        return value


COMMANDS = {
    "SET": cmd_set,
    "GET": cmd_get,
}


def process_command(line: str) -> str:
    # поддерживаем простую текстовую форму: one-line / command args...
    parts = line.strip().split()
    if not parts:
        return "ERR Empty command"
    cmd, *args = parts
    func = COMMANDS.get(cmd.upper())
    if not func:
        return "ERR Unknown command"
    return func(args)


def cleanup_expired_keys(interval: float = 1.0):
    while True:
        time.sleep(interval)
        now = time.time()
        with lock:
            # копируем ключи, чтобы безопасно итерироваться
            for k, (_, exp) in list(data_store.items()):
                if exp is not None and now > exp:
                    del data_store[k]


def handle_client(conn: socket.socket, addr):
    with conn:
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    return
                # поддержка нескольких команд в одном буфере — делим по переводам строк
                for raw in data.decode(errors="ignore").splitlines():
                    line = raw.strip()
                    if not line:
                        # пустые строки игнорируем, чтобы telnet не ломал сессию
                        continue
                    resp = process_command(line)
                    conn.sendall((resp + "\n").encode())
        except Exception:
            # сервер не падает из-за одного клиента
            return


def main():
    ap = argparse.ArgumentParser(description="Tiny Redis-like TCP cache")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=6379)
    ap.add_argument("--gc-interval", type=float, default=1.0, help="TTL cleanup interval, seconds")
    args = ap.parse_args()

    threading.Thread(target=cleanup_expired_keys, args=(args.gc_interval,), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # небольшая защита от 'address already in use'
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((args.host, args.port))
        s.listen()
        print(f"Server listening on {args.host}:{args.port}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
