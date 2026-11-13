<div align="center">

<img src="assets/banner.svg" alt="portwatch" width="100%">

<p>
  <img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge">
  <img alt="Python" src="https://img.shields.io/badge/python-3.8%2B-fbbf24?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Linux-fb923c?style=for-the-badge&logo=linux&logoColor=white">
  <img alt="Dependencies" src="https://img.shields.io/badge/dependencies-zero-38bdf8?style=for-the-badge">
</p>

**"Address already in use"? Find the culprit and free the port in seconds.**

</div>

---

## ✨ Features

- 📡 Lists every **listening TCP port** (IPv4 and IPv6) with PID, user and process name
- 🟡 Highlights ports reachable from **other machines** (`0.0.0.0` / `::`)
- 🔪 `--kill PORT` stops the owner, **after asking you**
- 👀 `--watch` refreshes live and flags **new** ports as they appear
- 🧾 `--json` for scripts
- 🪶 One file, reads `/proc` directly, no `lsof`/`ss` needed

## 🚀 Usage

```bash
git clone https://github.com/CyberLoop-dev/portwatch.git
cd portwatch

python3 portwatch.py              # everything listening
python3 portwatch.py 3000         # just one port
python3 portwatch.py --kill 3000  # free it (asks first, SIGTERM)
python3 portwatch.py --watch      # live view
sudo python3 portwatch.py         # also see other users' processes
```

Example:

```text
PORT   ADDRESS                 PID      USER        PROCESS
22     0.0.0.0                 811      root        sshd
3000   127.0.0.1               20417    alex        node
5432   127.0.0.1               902      postgres    postgres
```

## 🔐 Notes

- Without `sudo` you can only map sockets to processes you own; other rows show `-` for the PID.
- `--kill` sends `SIGTERM` by default. Add `--force` for `SIGKILL`.
- Linux only. On macOS use `lsof -nP -iTCP -sTCP:LISTEN`.
- TCP in LISTEN state only (UDP is out of scope for now).

## 📄 License

MIT
