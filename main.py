import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
import json
from datetime import datetime, timedelta
import time
import traceback
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
PRIORITY_ALERT_REPETITIONS = 3
DEFAULT_TIMEOUT = 10

class ShopeeMonitor:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_api = f"https://api.telegram.org/bot{telegram_bot_token}"
        self.state_file = "product_state.json"
        
        # Configure session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def get_wib_time(self):
        """Get current time in WIB (UTC+7)"""
        utc_time = datetime.utcnow()
        wib_time = utc_time + timedelta(hours=7)
        return wib_time.strftime('%Y-%m-%d %H:%M:%S WIB')
    
    def load_state(self):
        """Load status produk terakhir"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Load state warning: {e}")
        return {}
    
    def save_state(self, state):
        """Simpan status produk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info("State saved successfully")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def send_telegram(self, message, repeat=1):
        """Kirim pesan ke Telegram"""
        try:
            url = f"{self.telegram_api}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }
            
            success = False
            for attempt in range(repeat):
                response = self.session.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
                
                if response.status_code == 200:
                    logger.info(f"Telegram notification sent (attempt {attempt + 1}/{repeat})")
                    success = True
                    if attempt < repeat - 1:
                        time.sleep(0.5)  # Brief delay between repetitions
                else:
                    logger.error(f"Telegram error: {response.status_code}")
                    return False
            
            return success
                
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    def check_product(self, shop_id, item_id):
        """Cek produk Shopee dengan multiple methods"""
        
        # Method 1: Standard API
        try:
            logger.info("Trying standard API...")
            
            url = "https://shopee.co.id/api/v4/item/get"
            params = {
                'shopid': shop_id,
                'itemid': item_id
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://shopee.co.id/',
                'Accept': 'application/json',
                'Accept-Language': 'id-ID,id;q=0.9',
            }
            
            # Get cookies first
            self.session.get('https://shopee.co.id/', headers=headers, timeout=DEFAULT_TIMEOUT)
            time.sleep(1)
            
            # Get product data
            response = self.session.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    return None
                
                if isinstance(data, dict) and 'data' in data and data['data']:
                    item = data['data']
                    
                    # Safely extract fields
                    try:
                        price_raw = item.get('price', 0)
                        price = price_raw / 100000 if price_raw and price_raw > 0 else 0
                        stock = item.get('stock', 0)
                        
                        result = {
                            'name': item.get('name', 'Unknown'),
                            'stock': stock,
                            'price': price,
                            'available': stock > 0
                        }
                        
                        logger.info("Success!")
                        return result
                    except (TypeError, ZeroDivisionError, KeyError) as e:
                        logger.error(f"Error parsing item data: {e}")
                        return None
                     
        except Exception as e:
            logger.warning(f"Method 1 failed: {str(e)[:50]}")
        
        # Method 2: PC API
        try:
            logger.info("Trying PC API...")
            
            url = "https://shopee.co.id/api/v4/pdp/get_pc"
            params = {
                'shop_id': shop_id,
                'item_id': item_id,
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://shopee.co.id/',
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    return None
                
                if isinstance(data, dict) and 'item' in data:
                    item = data['item']
                    
                    # Safely extract fields
                    try:
                        price_raw = item.get('price', 0)
                        price = price_raw / 100000 if price_raw and price_raw > 0 else 0
                        stock = item.get('stock', 0)
                        
                        result = {
                            'name': item.get('name', 'Unknown'),
                            'stock': stock,
                            'price': price,
                            'available': stock > 0
                        }
                        
                        logger.info("Success!")
                        return result
                    except (TypeError, ZeroDivisionError, KeyError) as e:
                        logger.error(f"Error parsing item data: {e}")
                        return None
                    
        except Exception as e:
            logger.warning(f"Method 2 failed: {str(e)[:50]}")
        
        logger.error("All methods failed")
        return None
    
    def monitor_once(self, products):
        """Single monitoring check"""
        wib_time = self.get_wib_time()
        
        logger.info("=" * 60)
        logger.info("🤖 Shopee Monitor - Railway.app")
        logger.info(f"⏰ {wib_time}")
        logger.info("=" * 60)
        
        state = self.load_state()
        new_state = {}
        
        for idx, product in enumerate(products, 1):
            shop_id = product['shop_id']
            item_id = product['item_id']
            product_key = f"{shop_id}_{item_id}"
            
            logger.info(f"🔍 [{idx}/{len(products)}] Product: {product_key}")
            
            info = self.check_product(shop_id, item_id)
            
            if info:
                current_status = info['available']
                previous_status = state.get(product_key)
                
                logger.info(f"📦 {info['name']}")
                logger.info(f"💰 Rp {info['price']:,.0f}")
                logger.info(f"📊 Stock: {info['stock']}")
                logger.info(f"{'✅ READY' if current_status else '❌ HABIS'}")
                
                # Notify if changed
                if previous_status is not None and previous_status != current_status:
                    logger.info("🚨 STATUS CHANGED! Sending notification...")
                    
                    emoji = "✅" if current_status else "❌"
                    status = "READY" if current_status else "HABIS"
                    
                    message = (
                        f"{emoji} <b>PRODUK {status}!</b>\n\n"
                        f"📦 <b>{info['name']}</b>\n"
                        f"💰 Rp {info['price']:,.0f}\n"
                        f"📊 Stok: {info['stock']} unit\n"
                        f"🕐 {wib_time}\n\n"
                        f"🔗 <a href='https://shopee.co.id/product/{shop_id}/{item_id}'>{'BELI SEKARANG!' if current_status else 'Lihat Produk'}</a>"
                    )
                    
                    # Send priority alerts multiple times if product becomes available
                    repeat_count = PRIORITY_ALERT_REPETITIONS if current_status else 1
                    self.send_telegram(message, repeat=repeat_count)
                elif previous_status is None:
                    logger.info("ℹ️  First check, baseline saved")
                else:
                    logger.info("✓ No change")
                
                new_state[product_key] = current_status
            else:
                logger.error("Failed to fetch")
                if product_key in state:
                    new_state[product_key] = state[product_key]
        
        self.save_state(new_state)
        logger.info("=" * 60)
    
    def run_continuous(self, products, interval=300):
        """Run monitoring continuously"""
        logger.info("🚀 Starting continuous monitoring...")
        logger.info(f"⏱️  Check interval: {interval} seconds ({interval//60} minutes)")
        logger.info(f"📦 Products: {len(products)}")
        
        # Send startup notification
        wib_time = self.get_wib_time()
        startup_message = (
            f"🤖 <b>Shopee Monitor Started!</b>\n\n"
            f"✅ Railway.app deployment active\n"
            f"📦 Monitoring {len(products)} product(s)\n"
            f"⏱️  Interval: {interval//60} minutes\n"
            f"🕐 {wib_time}"
        )
        self.send_telegram(startup_message)
        
        try:
            while True:
                try:
                    self.monitor_once(products)
                    
                    logger.info(f"⏳ Waiting {interval} seconds until next check...")
                    logger.info(f"⏰ Next check in {interval//60} minutes")
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"Error during monitoring: {e}")
                    traceback.print_exc()
                    logger.info("⏳ Retrying in 60 seconds...")
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown requested by user")
            wib_time = self.get_wib_time()
            shutdown_message = f"🛑 <b>Bot Stopped</b>\n\n🕐 {wib_time}"
            self.send_telegram(shutdown_message)
            logger.info("Shutdown complete")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 SHOPEE TELEGRAM MONITOR - RAILWAY")
    logger.info("=" * 60)
    
    # Get credentials with validation
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    # Validate required environment variables
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ ERROR: Missing required environment variable: TELEGRAM_BOT_TOKEN")
        logger.error("   Please set TELEGRAM_BOT_TOKEN in your environment or .env file")
        sys.exit(1)
    
    if not TELEGRAM_CHAT_ID:
        logger.error("❌ ERROR: Missing required environment variable: TELEGRAM_CHAT_ID")
        logger.error("   Please set TELEGRAM_CHAT_ID in your environment or .env file")
        sys.exit(1)
    
    # Get check interval with validation
    try:
        CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '300'))
        # Ensure minimum interval of 60 seconds
        if CHECK_INTERVAL < 60:
            logger.warning(f"CHECK_INTERVAL {CHECK_INTERVAL}s is too low, using minimum of 60s")
            CHECK_INTERVAL = 60
    except ValueError:
        logger.warning("Invalid CHECK_INTERVAL value, using default of 300 seconds")
        CHECK_INTERVAL = 300
    
    logger.info(f"✅ Credentials loaded")
    logger.info(f"⏱️  Interval: {CHECK_INTERVAL}s ({CHECK_INTERVAL//60}min)")
    
    # Products to monitor
    PRODUCTS = [
        {
            'shop_id': '581472460',
            'item_id': '28841260015'
        }
    ]
    
    # Run bot
    bot = ShopeeMonitor(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    bot.run_continuous(PRODUCTS, interval=CHECK_INTERVAL)
