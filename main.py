import requests
import os
import json
from datetime import datetime, timedelta
import time
import traceback

class ShopeeMonitor:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_api = f"https://api.telegram.org/bot{telegram_bot_token}"
        self.state_file = "product_state.json"
        
    def get_wib_time(self):
        """Get current time in WIB (UTC+7)"""
        utc_time = datetime.utcnow()
        wib_time = utc_time + timedelta(hours=7)
        return wib_time.strftime('%Y-%m-%d %H:%M:%S')
    
    def load_state(self):
        """Load status produk terakhir"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️  Load state warning: {e}")
        return {}
    
    def save_state(self, state):
        """Simpan status produk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            print(f"💾 State saved successfully")
        except Exception as e:
            print(f"❌ Error saving state: {e}")
    
    def send_telegram(self, message):
        """Kirim pesan ke Telegram"""
        try:
            url = f"{self.telegram_api}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Telegram notification sent!")
                return True
            else:
                print(f"❌ Telegram error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False
    
    def check_product(self, shop_id, item_id):
        """Cek produk Shopee dengan multiple methods"""
        
        # Method 1: Standard API
        try:
            print(f"   📡 Trying standard API...")
            
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
            
            session = requests.Session()
            
            # Get cookies first
            session.get('https://shopee.co.id/', headers=headers, timeout=10)
            time.sleep(1)
            
            # Get product data
            response = session.get(url, params=params, headers=headers, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and data['data']:
                    item = data['data']
                    
                    result = {
                        'name': item.get('name', 'Unknown'),
                        'stock': item.get('stock', 0),
                        'price': item.get('price', 0) / 100000,
                        'available': item.get('stock', 0) > 0
                    }
                    
                    print(f"   ✅ Success!")
                    return result
                    
        except Exception as e:
            print(f"   ⚠️  Method 1 failed: {str(e)[:50]}")
        
        # Method 2: PC API
        try:
            print(f"   📡 Trying PC API...")
            
            url = "https://shopee.co.id/api/v4/pdp/get_pc"
            params = {
                'shop_id': shop_id,
                'item_id': item_id,
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://shopee.co.id/',
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'item' in data:
                    item = data['item']
                    
                    result = {
                        'name': item.get('name', 'Unknown'),
                        'stock': item.get('stock', 0),
                        'price': item.get('price', 0) / 100000,
                        'available': item.get('stock', 0) > 0
                    }
                    
                    print(f"   ✅ Success!")
                    return result
                    
        except Exception as e:
            print(f"   ⚠️  Method 2 failed: {str(e)[:50]}")
        
        print(f"   ❌ All methods failed")
        return None
    
    def monitor_once(self, products):
        """Single monitoring check"""
        wib_time = self.get_wib_time()
        
        print(f"\n{'='*60}")
        print(f"🤖 Shopee Monitor - Railway.app")
        print(f"⏰ {wib_time} WIB")
        print(f"{'='*60}\n")
        
        state = self.load_state()
        new_state = {}
        
        for idx, product in enumerate(products, 1):
            shop_id = product['shop_id']
            item_id = product['item_id']
            product_key = f"{shop_id}_{item_id}"
            
            print(f"🔍 [{idx}/{len(products)}] Product: {product_key}")
            
            info = self.check_product(shop_id, item_id)
            
            if info:
                current_status = info['available']
                previous_status = state.get(product_key)
                
                print(f"\n   📦 {info['name']}")
                print(f"   💰 Rp {info['price']:,.0f}")
                print(f"   📊 Stock: {info['stock']}")
                print(f"   {'✅ READY' if current_status else '❌ HABIS'}\n")
                
                # Notify if changed
                if previous_status is not None and previous_status != current_status:
                    print(f"   🚨 STATUS CHANGED! Sending notification...")
                    
                    emoji = "✅" if current_status else "❌"
                    status = "READY" if current_status else "HABIS"
                    
                    message = (
                        f"{emoji} <b>PRODUK {status}!</b>\n\n"
                        f"📦 <b>{info['name']}</b>\n"
                        f"💰 Rp {info['price']:,.0f}\n"
                        f"📊 Stok: {info['stock']} unit\n"
                        f"🕐 {wib_time} WIB\n\n"
                        f"🔗 <a href='https://shopee.co.id/product/{shop_id}/{item_id}'>{'BELI SEKARANG!' if current_status else 'Lihat Produk'}</a>"
                    )
                    
                    self.send_telegram(message)
                elif previous_status is None:
                    print(f"   ℹ️  First check, baseline saved")
                else:
                    print(f"   ✓ No change")
                
                new_state[product_key] = current_status
            else:
                print(f"   ❌ Failed to fetch")
                if product_key in state:
                    new_state[product_key] = state[product_key]
            
            print()        
        
        self.save_state(new_state)
        print(f"{'='*60}\n")
    
    def run_continuous(self, products, interval=300):
        """Run monitoring continuously"""
        print(f"🚀 Starting continuous monitoring...")
        print(f"⏱️  Check interval: {interval} seconds ({interval//60} minutes)")
        print(f"📦 Products: {len(products)}")
        print()        
        # Send startup notification
        wib_time = self.get_wib_time()
        self.send_telegram(
            "🤖 <b>Shopee Monitor Started!</b>\n\n"
            f"✅ Railway.app deployment active\n"
            f"📦 Monitoring {len(products)} product(s)\n"
            f"⏱️  Interval: {interval//60} minutes\n"
            f"🕐 {wib_time} WIB"
        )
        
        while True:
            try:
                self.monitor_once(products)
                
                print(f"⏳ Waiting {interval} seconds until next check...")
                print(f"⏰ Next check in {interval//60} minutes\n")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Stopped by user")
                wib_time = self.get_wib_time()
                self.send_telegram(f"🛑 <b>Bot Stopped</b>\n\n🕐 {wib_time} WIB")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                traceback.print_exc()
                print(f"\n⏳ Retrying in 60 seconds...\n")
                time.sleep(60)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 SHOPEE TELEGRAM MONITOR - RAILWAY")
    print("="*60 + "\n")
    
    # Get credentials
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '300'))  # Default 5 minutes
    
    # Validate
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ ERROR: Missing environment variables!")
        print("   Required: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
        exit(1)
    
    print(f"✅ Credentials loaded")
    print(f"⏱️  Interval: {CHECK_INTERVAL}s ({CHECK_INTERVAL//60}min)\n")
    
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
