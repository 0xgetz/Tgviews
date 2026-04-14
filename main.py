import aiohttp
import asyncio
from re import search, compile
from datetime import datetime
from fake_useragent import UserAgent
from aiohttp_socks import ProxyConnector
import os
import ssl
import sys
import socket
import random
import re

# Fix 2: UserAgent instantiated once at module level, reused across all coroutines
UA = UserAgent()

# Fix 3: REGEX updated to also accept user:pass@ip:port authenticated proxy format
REGEX = compile(
    r"^(?:[^@]+@)?(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}$"
)

def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

class Telegram:
    def __init__(self, channel: str, post: int, concurrency: int = 100, target_views: int = 0) -> None:
        # Parse channel from URL if provided
        if channel.startswith("https://t.me/"):
            channel = channel.split("/")[-1].replace('@', '')
        elif channel.startswith("t.me/"):
            channel = channel.split("/")[-1].replace('@', '')
        elif channel.startswith("@"):
            channel = channel[1:]

        self.channel = channel
        self.post = post
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)

        # Enhanced SSL context configuration
        self.ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

        self.target_views = target_views
        self.views_sent = 0
        self.lock = asyncio.Lock()
        log(f"Initialized with channel: @{channel}, post: {post}, concurrency: {concurrency}, target views: {target_views}")

    async def request(self, proxy: str, proxy_type: str):
        # Handle different proxy types
        proxy_url = f"{proxy_type}://{proxy}"
        try:
            async with self.semaphore:
                # Create appropriate connector based on proxy type
                if proxy_type in ["http", "https"]:
                    connector = aiohttp.TCPConnector(ssl=self.ssl_context)
                else:
                    connector = ProxyConnector.from_url(proxy_url, ssl=self.ssl_context)

                jar = aiohttp.CookieJar(unsafe=True)
                async with aiohttp.ClientSession(
                    cookie_jar=jar,
                    connector=connector,
                    headers={"Connection": "keep-alive"},
                    trust_env=True
                ) as session:
                    # Fix 2: reuse module-level UA instance instead of creating per-request
                    user_agent = UA.random
                    headers = {
                        "referer": f"https://t.me/{self.channel}/{self.post}",
                        "user-agent": user_agent,
                        "Pragma": "no-cache",
                        "Cache-Control": "no-store"
                    }

                    # First request to get cookies
                    embed_url = f"https://t.me/{self.channel}/{self.post}?embed=1&mode=tme"
                    async with session.get(
                        embed_url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                        allow_redirects=True
                    ) as embed_response:

                        # Check for stel_ssid cookie
                        if not jar.filter_cookies(embed_response.url).get("stel_ssid"):
                            log("ERROR: No stel_ssid cookie received")
                            return

                        # Extract view token
                        embed_text = await embed_response.text()
                        views_token = search('data-view="([^"]+)"', embed_text)
                        if not views_token:
                            log("ERROR: No view token found")
                            return

                    # Second request to register view
                    view_url = "https://t.me/v/?views=" + views_token.group(1)
                    view_headers = {
                        "referer": f"https://t.me/{self.channel}/{self.post}?embed=1&mode=tme",
                        "user-agent": user_agent,
                        "x-requested-with": "XMLHttpRequest",
                        "Content-Type": "application/x-www-form-urlencoded"
                    }

                    async with session.post(
                        view_url,
                        headers=view_headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as view_response:

                        view_text = await view_response.text()
                        if view_text == "true" and view_response.status == 200:
                            async with self.lock:
                                self.views_sent += 1
                                log(f"SUCCESS: View registered ({self.views_sent}/{self.target_views})")

                                # Check if target reached
                                if self.target_views > 0 and self.views_sent >= self.target_views:
                                    log(f"TARGET REACHED: {self.target_views} views sent!")
                                    # Cancel all tasks
                                    for task in asyncio.all_tasks():
                                        if task is not asyncio.current_task():
                                            task.cancel()
                        else:
                            log(f"FAILED: View not registered - {view_response.status} {view_text[:50]}...")

        except asyncio.CancelledError:
            raise  # Propagate cancellation
        except Exception as e:
            log(f"ERROR: Proxy connection failed - {proxy_type}://{proxy} - {str(e)[:50]}...")

    async def run_proxies_continuous(self, lines: list):
        log(f"Starting continuous mode with {len(lines)} proxies")

        tasks = []
        for proxy_type, proxy in lines:
            tasks.append(asyncio.create_task(self.request(proxy, proxy_type)))

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            log("View sending cancelled")
        finally:
            for task in tasks:
                task.cancel()

    async def continuous_request(self, proxy: str, proxy_type: str):
        while True:
            if self.target_views > 0 and self.views_sent >= self.target_views:
                return

            await self.request(proxy, proxy_type)
            await asyncio.sleep(1)  # Small delay between requests

    # Fix 4: Cancellation race fixed — collect ALL tasks before awaiting any,
    # so a mid-loop cancellation cannot leave orphaned coroutines.
    async def run_auto_continuous(self):
        log("Starting continuous auto mode")
        while True:
            if self.target_views > 0 and self.views_sent >= self.target_views:
                log("Target views reached. Exiting.")
                return

            auto = Auto()
            await auto.init()

            if not auto.proxies:
                log("No proxies found, retrying in 60 seconds...")
                await asyncio.sleep(60)
                continue

            log(f"Auto mode loaded {len(auto.proxies)} proxies from proxy.txt")

            # Build the full task list first, then await — prevents orphans on cancellation
            tasks = [
                asyncio.create_task(self.continuous_request(proxy, proxy_type))
                for proxy_type, proxy in auto.proxies
                if not (self.target_views > 0 and self.views_sent >= self.target_views)
            ]

            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                log("Auto mode cancelled")
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                return
            except Exception as e:
                log(f"Error in auto mode: {str(e)}")
                log("Rescanning proxies...")
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    # Fix 1: Implement run_rotated_continuous — rotates through the supplied proxy
    # list continuously, moving to the next proxy after each attempt or failure.
    async def run_rotated_continuous(self, proxies: list, default_protocol: str = "http"):
        """
        Rotate through a pre-supplied proxy list continuously.
        Each entry in proxies is either a (protocol, address) tuple or a raw string.
        After each attempt (success or failure) the next proxy in the list is used.
        Stops when target_views is reached (if set).
        """
        if not proxies:
            log("ERROR: No proxies supplied for rotate mode")
            return

        log(f"Starting rotate mode with {len(proxies)} proxies")
        index = 0

        while True:
            if self.target_views > 0 and self.views_sent >= self.target_views:
                log("Target views reached. Exiting rotate mode.")
                return

            entry = proxies[index % len(proxies)]
            if isinstance(entry, tuple):
                proxy_type, proxy_addr = entry
            else:
                # Raw string — parse protocol if present
                if "://" in entry:
                    proxy_type, proxy_addr = entry.split("://", 1)
                else:
                    proxy_type = default_protocol
                    proxy_addr = entry

            try:
                await self.request(proxy_addr, proxy_type)
            except asyncio.CancelledError:
                log("Rotate mode cancelled")
                return
            except Exception as e:
                log(f"Rotate: proxy {proxy_type}://{proxy_addr} failed — {str(e)[:60]}")

            index += 1
            await asyncio.sleep(0.5)  # Small delay between rotations


class Auto:
    def __init__(self):
        self.proxies = []
        # Multiple proxy sources with different protocols
        self.download_urls = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=all&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://www.proxy-list.download/api/v1/get?type=https",
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http,https,socks4,socks5"
        ]
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        ]

    async def init(self):
        self.proxies.clear()
        await self.download_proxies()
        await self.load_proxies()

    async def download_proxies(self):
        """Download proxies from multiple sources"""
        downloaded = False

        # Shuffle URLs to distribute load
        random.shuffle(self.download_urls)

        for url in self.download_urls:
            try:
                # Create SSL context for download
                ssl_context = ssl.create_default_context()
                ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')

                # Select random user agent
                headers = {
                    "User-Agent": random.choice(self.user_agents),
                    "Accept": "text/plain"
                }

                async with aiohttp.ClientSession() as session:
                    log(f"Trying proxy source: {url}")
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=15),
                        headers=headers,
                        ssl=ssl_context
                    ) as response:
                        if response.status == 200:
                            content = await response.text()
                            if content.strip():
                                with open("proxy.txt", "w") as f:
                                    f.write(content)
                                log(f"Downloaded {len(content.splitlines())} proxies from {url}")
                                downloaded = True
                                break
                            else:
                                log("Received empty response, trying next source")
                        else:
                            log(f"Failed to download proxies. Status code: {response.status}")
            except Exception as e:
                log(f"Proxy download error from {url}: {str(e)[:100]}")

        if not downloaded:
            log("All proxy sources failed! Using existing proxy.txt if available")

    async def load_proxies(self):
        """Load proxies exclusively from proxy.txt with protocol detection"""
        try:
            if not os.path.exists("proxy.txt"):
                log("proxy.txt not found, skipping load")
                return

            valid_proxies = []
            invalid_count = 0
            with open("proxy.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # Extract protocol from line
                    protocol = "http"  # default protocol
                    if "://" in line:
                        protocol_part, address = line.split("://", 1)
                        protocol = protocol_part.lower()
                    else:
                        address = line

                    # Handle different formats: ip:port or protocol:ip:port
                    parts = address.split(':')

                    if len(parts) == 2:
                        # Format: ip:port
                        ip, port = parts
                    elif len(parts) == 3:
                        # Format: protocol:ip:port (but protocol already extracted)
                        ip, port = parts[0], parts[2]
                    else:
                        invalid_count += 1
                        continue

                    # Normalize protocol names
                    if protocol in ["socks4", "socks4a"]:
                        protocol = "socks4"
                    elif protocol in ["socks5", "socks5h"]:
                        protocol = "socks5"
                    elif protocol in ["http", "https"]:
                        pass
                    else:
                        invalid_count += 1
                        continue

                    # Validate IP address
                    try:
                        socket.inet_aton(ip)
                    except socket.error:
                        invalid_count += 1
                        continue

                    # Validate port
                    try:
                        port_num = int(port)
                        if not (1 <= port_num <= 65535):
                            invalid_count += 1
                            continue
                    except ValueError:
                        invalid_count += 1
                        continue

                    # Reconstruct proxy string
                    proxy_str = f"{ip}:{port}"

                    # Check with regex (plain ip:port at this point, always valid)
                    if REGEX.match(proxy_str):
                        valid_proxies.append((protocol, proxy_str))
                    else:
                        invalid_count += 1

            self.proxies = valid_proxies
            log(f"Loaded {len(self.proxies)} valid proxies")
            if invalid_count > 0:
                log(f"Skipped {invalid_count} invalid proxies")

            # Log protocol distribution
            protocol_count = {}
            for protocol, _ in self.proxies:
                protocol_count[protocol] = protocol_count.get(protocol, 0) + 1

            for protocol, count in protocol_count.items():
                log(f" - {protocol.upper()}: {count} proxies")

        except Exception as e:
            log(f"Error loading proxy.txt: {str(e)}")


def get_user_input():
    """Get user input for channel URL and viewer count"""
    print("\nTelegram View Booster")
    print("---------------------")

    # Get channel URL
    channel_url = input("Enter Telegram channel URL (e.g., https://t.me/channel or @channel): ").strip()
    if not channel_url:
        log("Channel URL is required!")
        sys.exit(1)

    # Get post ID
    post_id = input("Enter post ID (number after the channel name in URL): ").strip()
    if not post_id.isdigit():
        log("Post ID must be a number!")
        sys.exit(1)
    post_id = int(post_id)

    # Get target views
    target_views = input("Enter number of views to send (0 for unlimited): ").strip()
    if not target_views.isdigit():
        log("View count must be a number!")
        sys.exit(1)
    target_views = int(target_views)

    # Get mode
    print("\nAvailable modes:")
    print("1. Auto   - Download proxies automatically and run continuously")
    print("2. List   - Load proxies from a local file and send views")
    print("3. Rotate - Use a supplied proxy list, rotating to the next proxy after each attempt")
    mode_choice = input("Select mode (1-3): ").strip()

    mode_map = {
        "1": "auto",
        "2": "list",
        "3": "rotate"
    }

    mode = mode_map.get(mode_choice, "auto")

    # Get proxy file / list if needed
    proxy_input = ""
    if mode == "list":
        proxy_input = input("Enter path to proxy file: ").strip()
        if not os.path.exists(proxy_input):
            log("Proxy file not found!")
            sys.exit(1)
    elif mode == "rotate":
        proxy_input = input(
            "Enter path to proxy file for rotation\n"
            "  (one proxy per line, format: [protocol://][user:pass@]ip:port): "
        ).strip()
        if not os.path.exists(proxy_input):
            log("Proxy file not found!")
            sys.exit(1)

    # Get concurrency
    concurrency = input("Enter concurrency level (default 200): ").strip()
    if not concurrency:
        concurrency = 200
    elif not concurrency.isdigit():
        log("Concurrency must be a number! Using default 200")
        concurrency = 200
    else:
        concurrency = int(concurrency)

    return {
        "channel": channel_url,
        "post": post_id,
        "mode": mode,
        "proxy": proxy_input,
        "concurrency": concurrency,
        "target_views": target_views
    }


def parse_proxy_file(path: str) -> list:
    """Parse a proxy file into a list of (protocol, address) tuples.
    Accepts lines in any of these formats:
      ip:port
      protocol://ip:port
      user:pass@ip:port
      protocol://user:pass@ip:port
    """
    proxies = []
    with open(path, "r") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            protocol = "http"
            address = line

            if "://" in line:
                protocol, address = line.split("://", 1)
                protocol = protocol.lower()

            # Normalize protocol
            if protocol in ("socks4", "socks4a"):
                protocol = "socks4"
            elif protocol in ("socks5", "socks5h"):
                protocol = "socks5"
            elif protocol not in ("http", "https"):
                protocol = "http"

            # Fix 3: validate with updated regex that accepts user:pass@ip:port
            if REGEX.match(address):
                proxies.append((protocol, address))
            else:
                log(f"Skipping invalid proxy: {line}")

    return proxies


async def main():
    user_input = get_user_input()

    log(f"Starting Telegram View Booster with mode: {user_input['mode']}")
    api = Telegram(
        user_input["channel"],
        user_input["post"],
        user_input["concurrency"],
        user_input["target_views"]
    )

    if user_input["mode"] == "list":
        proxies = parse_proxy_file(user_input["proxy"])
        log(f"Loaded {len(proxies)} proxies from file {user_input['proxy']}")
        await api.run_proxies_continuous(proxies)

    elif user_input["mode"] == "rotate":
        # Fix 1: pass full proxy list to run_rotated_continuous
        proxies = parse_proxy_file(user_input["proxy"])
        log(f"Loaded {len(proxies)} proxies for rotate mode from {user_input['proxy']}")
        await api.run_rotated_continuous(proxies)

    else:  # auto mode
        await api.run_auto_continuous()


if __name__ == "__main__":
    log("Program started")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Program terminated by user")
    except Exception as e:
        log(f"Unhandled exception: {str(e)}")
