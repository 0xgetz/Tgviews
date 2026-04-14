# Telegram View Booster

Boost Telegram post view counts by routing requests through proxies using async Python.

---

## 1. Installation

```bash
pip install -r requirements.txt
```

---

## 2. Running the Program

```bash
python main.py
```

---

## 3. Input Guide

The program will prompt for the following:

1. **Telegram channel URL**
   Enter the full channel URL or username.
   Examples: `https://t.me/my_channel`, `@my_channel`, `my_channel`

2. **Post ID**
   The numeric ID after the channel name in the post URL.
   Example: for `https://t.me/my_channel/123` enter `123`

3. **Number of views**
   How many views to send. Enter `0` for unlimited.

4. **Mode** (see below for details)

5. **Proxy input** (modes 2 and 3 only)

6. **Concurrency level**
   Number of simultaneous requests (default: 200).

---

## 4. Modes

### Mode 1 — Auto
Downloads fresh proxy lists automatically from multiple public sources, then sends views continuously. Rescans proxies after each cycle.

```
Select mode (1-3): 1
Enter concurrency level (default 200): 200
```

### Mode 2 — List
Loads proxies from a local file you provide. Each line should be one proxy in any of these formats:
- `ip:port`
- `protocol://ip:port`
- `user:pass@ip:port`
- `protocol://user:pass@ip:port`

Supported protocols: `http`, `https`, `socks4`, `socks5`

```
Select mode (1-3): 2
Enter path to proxy file: proxies.txt
Enter concurrency level (default 200): 200
```

### Mode 3 — Rotate
Uses a proxy file you supply, rotating to the next proxy after each request attempt (success or failure). Useful when you want deterministic control over which proxies are used and in what order.

Proxy file format is the same as Mode 2 (one proxy per line).

```
Select mode (1-3): 3
Enter path to proxy file for rotation: proxies.txt
Enter concurrency level (default 200): 200
```

---

## 5. Example Session

```
Telegram View Booster
---------------------
Enter Telegram channel URL (e.g., https://t.me/channel or @channel): https://t.me/my_channel
Enter post ID (number after the channel name in URL): 42
Enter number of views to send (0 for unlimited): 500

Available modes:
1. Auto   - Download proxies automatically and run continuously
2. List   - Load proxies from a local file and send views
3. Rotate - Use a supplied proxy list, rotating to the next proxy after each attempt
Select mode (1-3): 1
Enter concurrency level (default 200): 200
```

---

## 6. Monitoring

While running you will see real-time logs:
- Proxy download status (Auto mode)
- Number of valid proxies loaded
- Per-request success / failure with running view count
- Target-reached notification (if a target was set)

Press `Ctrl+C` at any time to stop.

---

## 7. Notes

- In Auto mode `proxy.txt` is overwritten on every cycle with freshly downloaded proxies.
- SSL errors: ensure your system has up-to-date CA certificates.
- Higher concurrency is faster but uses more memory and file descriptors.
- If all proxy sources fail in Auto mode, the program retries after 60 seconds using any existing `proxy.txt`.
