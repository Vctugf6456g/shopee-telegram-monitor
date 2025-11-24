import os
import json
import time
import traceback
import requests
from datetime import datetime, timedelta

# ========= Structured Logging Helper =========
def log(level: str, message: str, **extra):
    if not message or message.strip() == "":
        message = "<EMPTY_MESSAGE>"
    utc = datetime.utcnow()
    wib = utc + timedelta(hours=7)
    entry = {
        "ts_utc": utc.isoformat(timespec="seconds") + "Z",
        "ts_wib": wib.strftime("%Y-%m-%d %H:%M:%S"),
        "level": level.upper(),
        "message": message,
        "extra": extra
    }
    print(json.dumps(entry), flush=True)

# ========= Safe HTTP Request with Retry =========
def safe_request(session_or_module, url, params=None, headers=None,
                 retries=3, delay=1.5, tag=""):
    for attempt in range(1, retries + 1):
        try:
            resp = session_or_module.get(url, params=params, headers=headers, timeout=15)
            log("info", "HTTP request", tag=tag, attempt=attempt, status=resp.status_code, url=url)
            return resp
        except Exception as e:
            log("warning", "HTTP attempt failed", tag=tag, attempt=attempt, error=str(e))
            time.sleep(delay)
    log("error", "HTTP all retries failed", tag=tag, url=url)
    return None

class ShopeeMonitor:
    def __init__(self, telegram_bot_token: str, telegram_chat_id: str, state_file: str = "product_state.json"):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_api = f"https://api.telegram.org/bot{telegram_bot_token}"
        self.state_file = state_file
        self.session = requests.Session()
        log("info", "ShopeeMonitor initialized", state_file=state_file)

    def get_wib_time(self) -> str:
        utc_time = datetime.utcnow()
        return (utc_time + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")

    def load_state(self) -> dict:
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    log("info", "State loaded", entries=len(data))
                    return data
        except Exception as e:
            log("warning", "Failed loading state", error=str(e))
        return {}

    def save_state(self, state: dict):
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
            log("info", "State saved", entries=len(state))
        except Exception as e:
            log("error", "Failed saving state", error=str(e))

    def send_telegram(self, message: str) -> bool:
        if not message or message.strip() == "":
            message = "<EMPTY_MESSAGE>"
        try:
            url = f"{self.telegram_api}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                log("info", "Telegram sent", length=len(message))
                return True
            else:
                log("error", "Telegram failed", status_code=resp.status_code, body=resp.text[:250])
        except Exception as e:
            log("error", "Telegram exception", error=str(e))
        return False

    def _headers(self):
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            "Referer": "https://shopee.co.id/",
            "Accept": "application/json",
            "Accept-Language": "id-ID,id;q=0.9",
        }

    def check_product(self, shop_id: str, item_id: str) -> dict | None:
        headers = self._headers()

        # Method 1
        log("info", "Checking product (method1)", shop_id=shop_id, item_id=item_id)
        # Bootstrap cookies
        safe_request(self.session, "https://shopee.co.id/", headers=headers, tag="cookie-bootstrap")
        time.sleep(0.3)
        resp1 = safe_request(self.session, "https://shopee.co.id/api/v4/item/get",
                             params={"shopid": shop_id, "itemid": item_id},
                             headers=headers, tag="method1")

        if resp1 and resp1.status_code == 200:
            try:
                data = resp1.json()
                if data.get("data"):
                    item = data["data"]
                    raw_price = item.get("price", 0)
                    price_rp = (raw_price / 100000) if isinstance(raw_price, (int, float)) else 0
                    stock = item.get("stock", 0) or 0
                    result = {
                        "name": item.get("name", "Unknown"),
                        "stock": stock,
                        "price": price_rp,
                        "available": stock > 0,
                        "source": "method1"
                    }
                    log("info", "Method1 success", name=result["name"], stock=stock, price=price_rp)
                    return result
                else:
                    log("warning", "Method1 no usable data", keys=list(data.keys()))
            except Exception as e:
                log("warning", "Method1 parse error", error=str(e))

        # Method 2
        log("info", "Checking product (method2)", shop_id=shop_id, item_id=item_id)
        resp2 = safe_request(requests, "https://shopee.co.id/api/v4/pdp/get_pc",
                             params={"shop_id": shop_id, "item_id": item_id},
                             headers=headers, tag="method2")

        if resp2 and resp2.status_code == 200:
            try:
                data2 = resp2.json()
                if data2.get("item"):
                    item2 = data2["item"]
                    raw_price = item2.get("price", 0)
                    price_rp = (raw_price / 100000) if isinstance(raw_price, (int, float)) else 0
                    stock = item2.get("stock", 0) or 0
                    result = {
                        "name": item2.get("name", "Unknown"),
                        "stock": stock,
                        "price": price_rp,
                        "available": stock > 0,
                        "source": "method2"
                    }
                    log("info", "Method2 success", name=result["name"], stock=stock, price=price_rp)
                    return result
                else:
                    log("warning", "Method2 no item field", keys=list(data2.keys()))
            except Exception as e:
                log("warning", "Method2 parse error", error=str(e))

        log("error", "All methods failed", shop_id=shop_id, item_id=item_id)
        return None

    def monitor_once(self, products: list[dict]):
        wib_time = self.get_wib_time()
        log("info", "Monitor pass started", wib_time=wib_time, products=len(products))
        state = self.load_state()
        new_state = {}

        for idx, product in enumerate(products, start=1):
            shop_id = product["shop_id"]
            item_id = product["item_id"]
            key = f"{shop_id}_{item_id}"
            log("info", "Processing product", index=idx, total=len(products), key=key)

            info = self.check_product(shop_id, item_id)
            if info:
                current = info["available"]
                prev = state.get(key)
                log("info", "Fetched product status",
                    key=key, name=info["name"], stock=info["stock"],
                    price=info["price"], available=current, source=info["source"])

                if prev is not None and prev != current:
                    emoji = "✅" if current else "❌"
                    status_word = "READY" if current else "HABIS"
                    log("info", "Status changed", key=key, previous=prev, current=current)

                    msg = (
                        f"{emoji} <b>PRODUK {status_word}!</b>\n\n"
                        f"📦 <b>{info['name']}</b>\n"
                        f"💰 Rp {info['price']:,.0f}\n"
                        f"📊 Stok: {info['stock']} unit\n"
                        f"🕐 {wib_time} WIB\n\n"
                        f"🔗 <a href='https://shopee.co.id/product/{shop_id}/{item_id}'>"
                        f"{'BELI SEKARANG!' if current else 'Lihat Produk'}</a>"
                    )
                    self.send_telegram(msg)
                elif prev is None:
                    log("info", "Baseline stored", key=key, status=current)
                else:
                    log("info", "No change", key=key, status=current)

                new_state[key] = current
            else:
                log("warning", "Product fetch failed", key=key)
                if key in state:
                    new_state[key] = state[key]

        self.save_state(new_state)
        changed = sum(1 for k, v in new_state.items() if state.get(k) != v)
        failures = sum(1 for p in products if f"{p['shop_id']}_{p['item_id']}" not in new_state)
        log("info", "Monitor summary",
            total_products=len(products), changed=changed, failures=failures)
        log("info", "Monitor pass ended", wib_time=self.get_wib_time())

    def run_continuous(self, products: list[dict], interval: int = 300):
        wib_start = self.get_wib_time()
        self.send_telegram(
            "🤖 <b>Shopee Monitor Started!</b>\n\n"
            f"✅ Railway.app deployment active\n"
            f"📦 Monitoring {len(products)} product(s)\n"
            f"⏱️  Interval: {interval//60} minute(s)\n"
            f"🕐 {wib_start} WIB"
        )
        log("info", "Continuous loop started", interval_seconds=interval, products=len(products))

        while True:
            try:
                self.monitor_once(products)
                log("info", "Sleeping", seconds=interval)
                time.sleep(interval)
            except KeyboardInterrupt:
                log("info", "KeyboardInterrupt - stopping")
                self.send_telegram(f"🛑 <b>Bot Stopped</b>\n\n🕐 {self.get_wib_time()} WIB")
                break
            except Exception as e:
                log("error", "Unhandled loop exception", error=str(e),
                    stack=traceback.format_exc().splitlines()[-5:])
                self.send_telegram(
                    f"⚠️ <b>Loop Error</b>\n{str(e)}\nRetrying in 60s\n🕐 {self.get_wib_time()} WIB"
                )
                time.sleep(60)

def validate_env():
    missing = [v for v in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"] if not os.getenv(v)]
    if missing:
        log("error", "Missing required env vars", vars=missing)
        raise SystemExit(1)
    log("info", "Environment OK", vars="present")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SHOPEE TELEGRAM MONITOR - RAILWAY")
    print("=" * 60)
    validate_env()

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

    log("info", "Startup config",
        interval_seconds=CHECK_INTERVAL,
        interval_minutes=CHECK_INTERVAL // 60)

    PRODUCTS = [
        {"shop_id": "581472460", "item_id": "28841260015"}
        # Tambah produk lain di sini jika perlu
    ]

    monitor = ShopeeMonitor(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    monitor.run_continuous(PRODUCTS, interval=CHECK_INTERVAL)
