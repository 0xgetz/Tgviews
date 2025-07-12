import aiohttp
import asyncio
from re import search, compile
from datetime import datetime
from fake_useragent import UserAgent
from aiohttp_socks import ProxyConnector
import os
import ssl
import sys

# Regular expression for matching proxy patterns
REGEX = compile(
    r"(?:^|\D)?(("+ r"(?:[1-9]|[1-9]\d|1\d{2}|2[0-4]\d|25[0-5])"
    + r"\." + r"(?:\d|[1-9]\d|1\d{2}|2[0-4]\d|25[0-5])"
    + r"\." + r"(?:\d|[1-9]\d|1\d{2}|2[0-4]\d|25[0-5])"
    + r"\." + r"(?:\d|[1-9]\d|1\d{2}|2[0-4]\d|25[0-5])"
    + r"):" + (r"(?:\d|[1-9]\d{1,3}|[1-5]\d{4}|6[0-4]\d{3}"
    + r"|65[0-4]\d{2}|655[0-2]\d|6553[0-5])")
    + r")(?:\D|$)"
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
        proxy_url = f"{proxy_type}://{proxy}"
        try:
            async with self.semaphore:
                connector = ProxyConnector.from_url(proxy_url, ssl=self.ssl_context)
                jar = aiohttp.CookieJar(unsafe=True)
                async with aiohttp.ClientSession(
                    cookie_jar=jar,
                    connector=connector,
                    headers={"Connection": "keep-alive"},
                    trust_env=True
                ) as session:
                    user_agent = UserAgent().random
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

    async def run_proxies_continuous(self, lines: list, proxy_type: str):
        log(f"Starting continuous mode with {len(lines)} proxies of type {proxy_type}")
        
        tasks = []
        for proxy in lines:
            tasks.append(asyncio.create_task(self.request(proxy, proxy_type))
        
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
            await asyncio.sleep(1)  # Add small delay between requests

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
            
            tasks = []
            for proxy_type, proxy in auto.proxies:
                if self.target_views > 0 and self.views_sent >= self.target_views:
                    break
                    
                task = asyncio.create_task(self.continuous_request(proxy, proxy_type))
                tasks.append(task)
                await asyncio.sleep(0.1)  # Stagger task creation
            
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                log("Auto mode cancelled")
                return
            except Exception as e:
                log(f"Error in auto mode: {str(e)}")
                log("Rescanning proxies...")

class Auto:
    def __init__(self):
        self.proxies = []
        self.download_url = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport"

    async def init(self):
        self.proxies.clear()
        await self.download_proxies()
        await self.load_proxies()
    
    async def download_proxies(self):
        """Download proxies from API and save to proxy.txt"""
        try:
            # Create SSL context for download
            ssl_context = ssl.create_default_context()
            ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.download_url, 
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={"User-Agent": UserAgent().random},
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        with open("proxy.txt", "w") as f:
                            f.write(content)
                        log(f"Downloaded {len(content.splitlines())} proxies to proxy.txt")
                    else:
                        log(f"Failed to download proxies. Status code: {response.status}")
        except Exception as e:
            log(f"Proxy download error: {str(e)}")

    async def load_proxies(self):
        """Load proxies exclusively from proxy.txt"""
        try:
            if not os.path.exists("proxy.txt"):
                log("proxy.txt not found, skipping load")
                return
                
            with open("proxy.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(':', 2)
                    if len(parts) == 3:
                        protocol = parts[0].lower()
                        proxy = f"{parts[1]}:{parts[2]}"
                        if REGEX.fullmatch(proxy):
                            self.proxies.append((protocol, proxy))
            log(f"Loaded {len(self.proxies)} valid proxies")
        except Exception as e:
            log(f"Error loading proxy.txt: {str(e)}")

def get_user_input():
    """Get user input for channel URL and viewer count"""
    print("\n🚀 Telegram View Booster 🚀")
    print("---------------------------")
    
    # Get channel URL
    channel_url = input("Enter Telegram channel URL (e.g., https://t.me/channel or @channel): ").strip()
    if not channel_url:
        log("❌ Channel URL is required!")
        sys.exit(1)
        
    # Get post ID
    post_id = input("Enter post ID (number after the channel name in URL): ").strip()
    if not post_id.isdigit():
        log("❌ Post ID must be a number!")
        sys.exit(1)
    post_id = int(post_id)
    
    # Get target views
    target_views = input("Enter number of views to send (0 for unlimited): ").strip()
    if not target_views.isdigit():
        log("❌ View count must be a number!")
        sys.exit(1)
    target_views = int(target_views)
    
    # Get mode
    print("\n📡 Available modes:")
    print("1. Auto (download and use proxies automatically)")
    print("2. List (use proxies from a file)")
    print("3. Rotate (use a single proxy with rotation)")
    mode_choice = input("Select mode (1-3): ").strip()
    
    mode_map = {
        "1": "auto",
        "2": "list",
        "3": "rotate"
    }
    
    mode = mode_map.get(mode_choice, "auto")
    
    # Get proxy file if needed
    proxy_file = ""
    if mode == "list":
        proxy_file = input("Enter path to proxy file: ").strip()
        if not os.path.exists(proxy_file):
            log("❌ Proxy file not found!")
            sys.exit(1)
    elif mode == "rotate":
        proxy_file = input("Enter proxy (user:pass@ip:port or ip:port): ").strip()
    
    # Get concurrency
    concurrency = input("Enter concurrency level (default 200): ").strip()
    if not concurrency:
        concurrency = 200
    elif not concurrency.isdigit():
        log("❌ Concurrency must be a number! Using default 200")
        concurrency = 200
    else:
        concurrency = int(concurrency)
    
    return {
        "channel": channel_url,
        "post": post_id,
        "mode": mode,
        "proxy": proxy_file,
        "concurrency": concurrency,
        "target_views": target_views
    }

async def main():
    # Get user input
    user_input = get_user_input()
    
    log(f"🚀 Starting Telegram View Booster with mode: {user_input['mode']}")
    api = Telegram(
        user_input["channel"],
        user_input["post"],
        user_input["concurrency"],
        user_input["target_views"]
    )
    
    if user_input["mode"] == "list":
        with open(user_input["proxy"], "r") as file:
            lines = file.read().splitlines()
        log(f"📋 Loaded {len(lines)} proxies from file {user_input['proxy']}")
        await api.run_proxies_continuous(lines, "http")

    elif user_input["mode"] == "rotate":
        log(f"🔄 Starting rotated mode with proxy: {user_input['proxy']}")
        await api.run_rotated_continuous(user_input["proxy"], "http")

    else:  # auto mode
        await api.run_auto_continuous()

if __name__ == "__main__":
    log("📡 Program started")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("🛑 Program terminated by user")
    except Exception as e:
        log(f"❌ Unhandled exception: {str(e)}")
