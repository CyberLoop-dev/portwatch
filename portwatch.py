#!/usr/bin/env python3
"""portwatch: see who is listening on which port, and free a port in one command.

Linux only (reads /proc, no dependencies). Run with sudo to see other users' processes.
"""
import argparse
import json
import os
import pwd
import signal
import socket
import struct
import sys
import time

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else str(text)


def decode_addr(hexaddr, v6):
    if not v6:
        return socket.inet_ntoa(struct.pack("<I", int(hexaddr, 16)))
    raw = b"".join(struct.pack("<I", int(hexaddr[i:i + 8], 16)) for i in range(0, 32, 8))
    return socket.inet_ntop(socket.AF_INET6, raw)


def read_table(path, v6):
    rows = []
    try:
        f = open(path)
    except OSError:
        return rows
    with f:
        next(f, None)  # header
        for line in f:
            p = line.split()
            if len(p) < 10 or p[3] != "0A":  # 0A = LISTEN
                continue
            addr, port = p[1].rsplit(":", 1)
            rows.append({"proto": "tcp6" if v6 else "tcp", "addr": decode_addr(addr, v6),
                         "port": int(port, 16), "inode": p[9]})
    return rows


def inode_owners():
    owners = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        fd_dir = f"/proc/{pid}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue  # gone, or not ours
        for fd in fds:
            try:
                target = os.readlink(f"{fd_dir}/{fd}")
            except OSError:
                continue
            if target.startswith("socket:["):
                owners[target[8:-1]] = int(pid)
    return owners


def proc_info(pid):
    info = {"pid": pid, "name": "?", "user": "?", "cmd": ""}
    try:
        with open(f"/proc/{pid}/comm") as f:
            info["name"] = f.read().strip()
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            info["cmd"] = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
        uid = os.stat(f"/proc/{pid}").st_uid
        try:
            info["user"] = pwd.getpwuid(uid).pw_name
        except KeyError:
            info["user"] = str(uid)
    except OSError:
        pass
    return info


def snapshot():
    rows = read_table("/proc/net/tcp", False) + read_table("/proc/net/tcp6", True)
    owners = inode_owners()
    out, seen = [], set()
    for r in rows:
        pid = owners.get(r["inode"])
        key = (r["port"], pid, r["addr"])
        if key in seen:
            continue
        seen.add(key)
        info = proc_info(pid) if pid else {"pid": None, "name": "?", "user": "?", "cmd": ""}
        out.append({**r, **info})
    out.sort(key=lambda x: (x["port"], x["addr"]))
    return out


def print_table(rows, new_ports=()):
    print(c("1", f"{'PORT':<7}{'ADDRESS':<24}{'PID':<9}{'USER':<12}{'PROCESS'}"))
    for r in rows:
        exposed = r["addr"] in ("0.0.0.0", "::")
        addr = c("33", r["addr"]) if exposed else r["addr"]
        pad = " " * max(1, 24 - len(r["addr"]))
        pid = str(r["pid"]) if r["pid"] else "-"
        tag = c("1;32", "  NEW") if r["port"] in new_ports else ""
        print(f"{c('1;36', r['port']):<{7 + (len(c('1;36', r['port'])) - len(str(r['port'])))}}{addr}{pad}{pid:<9}{r['user']:<12}{r['name']}{tag}")
    print(c("2", f"\n{len(rows)} listening socket(s). Yellow = reachable from other machines (0.0.0.0 / ::)."))
    if any(r["pid"] is None for r in rows):
        print(c("2", "Some owners are hidden: run with sudo to see every process."))


def kill_port(port, force):
    rows = [r for r in snapshot() if r["port"] == port and r["pid"]]
    if not rows:
        sys.exit(f"portwatch: nothing visible is listening on port {port}")
    pids = sorted({r["pid"] for r in rows})
    for pid in pids:
        info = proc_info(pid)
        print(f"Port {port} is held by {c('1', info['name'])} (pid {pid}, user {info['user']})")
        print(c("2", "  " + (info["cmd"][:100] or "")))
        if input("Send SIGTERM? [y/N] ").strip().lower() != "y":
            print("skipped")
            continue
        try:
            os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
            print(c("32", "signal sent"))
        except PermissionError:
            print(c("31", "permission denied (try sudo)"))
        except ProcessLookupError:
            print("already gone")


def main():
    if not os.path.isdir("/proc/net"):
        sys.exit("portwatch needs Linux (/proc). On macOS try: lsof -nP -iTCP -sTCP:LISTEN")
    ap = argparse.ArgumentParser(description="Show listening TCP ports and the processes behind them.")
    ap.add_argument("port", nargs="?", type=int, help="only show this port")
    ap.add_argument("--kill", action="store_true", help="stop the process holding PORT (asks first)")
    ap.add_argument("--force", action="store_true", help="use SIGKILL instead of SIGTERM with --kill")
    ap.add_argument("--watch", action="store_true", help="refresh every 2 seconds and flag new ports")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()

    if a.kill:
        if a.port is None:
            ap.error("--kill needs a PORT")
        return kill_port(a.port, a.force)

    def view():
        rows = snapshot()
        return [r for r in rows if a.port is None or r["port"] == a.port]

    if a.json:
        print(json.dumps(view(), indent=2))
    elif a.watch:
        known = {r["port"] for r in view()}
        try:
            while True:
                rows = view()
                fresh = {r["port"] for r in rows} - known
                os.system("clear")
                print(c("2", time.strftime("%H:%M:%S") + "  (Ctrl+C to quit)\n"))
                print_table(rows, fresh)
                known |= {r["port"] for r in rows}
                time.sleep(2)
        except KeyboardInterrupt:
            pass
    else:
        print_table(view())


if __name__ == "__main__":
    main()
