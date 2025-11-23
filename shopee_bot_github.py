import requests
import os
import json
from datetime import datetime
import traceback
import time

class ShopeeMonitor:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_api = f"https://api.telegram.org/bot{telegram_bot_token}"
        self.state_file = "product_state.json"
        
    def load_state(self):
        """Load status produk terakhir dari file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning loading state: {e}")
        return {}
    
    def save_state(self, state):
        """Simpan status produk ke file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
            print(f"💾 State saved: {state}")
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
            
            print(f"📤 Sending to Telegram...")
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Telegram message sent successfully")
                return response.json()
            else:
                print(f"❌ Telegram API error: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error sending Telegram: {e}")
            return None
    
    def get_browser_headers(self):
        """Generate realistic browser headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://shopee.co.id/',
            'Origin': 'https://shopee.co.id',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'X-Requested-With': 'XMLHttpRequest',
            'X-Api-Source': 'pc',
        }
    
    def check_product_web_scraping(self, shop_id, item_id):
        """Alternatif: Scrape dari halaman web"""
        try:
            print(f"   🌐 Method 2: Web scraping...")
            
            # Buka halaman produk langsung
            url = f"https://shopee.co.id/api/v4/pdp/get_pc"
            params = {
                'shop_id': shop_id,
                'item_id': item_id,
            }
            
            headers = self.get_browser_headers()
            
            session = requests.Session()
            
            # First request to get cookies
            print(f"   🍪 Getting cookies...")
            session.get('https://shopee.co.id/', headers=headers, timeout=15)
            time.sleep(2)
            
            # Second request with cookies
            print(f"   📡 Fetching product data...")
            response = session.get(url, params=params, headers=headers, timeout=15)
            
            print(f"   📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if 'item' in data:
                    item = data['item']
                    
                    name = item.get('name', 'Unknown')
                    stock = item.get('stock', 0)
                    price = item.get('price', 0) / 100000
                    
                    return {
                        'name': name,
                        'stock': stock,
                        'price': price,
                        'available': stock > 0
                    }
            
            print(f"   ⚠️  Response: {response.text[:200]}")
            
        except Exception as e:
            print(f"   ❌ Web scraping failed: {e}")
        
        return None
    
    def check_product_mobile_api(self, shop_id, item_id):
        """Alternatif: Gunakan mobile API"""
        try:
            print(f"   📱 Method 3: Mobile API...")
            
            url = "https://shopee.co.id/api/v4/item/get"
            params = {
                'shopid': shop_id,
                'itemid': item_id
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                'Accept': 'application/json',
                'Referer': 'https://shopee.co.id/',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            print(f"   📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    item = data['data']
                    return {
                        'name': item.get('name', 'Unknown'),
                        'stock': item.get('stock', 0),
                        'price': item.get('price', 0) / 100000,
                        'available': item.get('stock', 0) > 0
                    }
            
        except Exception as e:
            print(f"   ❌ Mobile API failed: {e}")
        
        return None
    
    def check_product_html_scrape(self, shop_id, item_id):
        """Alternatif: Parse HTML langsung"""
        try:
            print(f"   🔍 Method 4: HTML scraping...")
            
            url = f"https://shopee.co.id/product/{shop_id}/{item_id}"
            headers = self.get_browser_headers()
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                html = response.text
                
                # Cari JSON data di HTML
                if '__INITIAL_STATE__' in html:
                    start = html.find('__INITIAL_STATE__=') + len('__INITIAL_STATE__=')
                    end = html.find('</script>', start)
                    json_str = html[start:end].strip()
                    
                    # Clean JSON
                    if json_str.endswith(';'):
                        json_str = json_str[:-1]
                    
                    data = json.loads(json_str)
                    
                    # Navigate through the data structure
                    if 'item' in data and 'models' in data['item']:
                        item_data = list(data['item']['models'].values())[0]
                        
                        return {
                            'name': item_data.get('name', 'Unknown'),
                            'stock': item_data.get('stock', 0),
                            'price': item_data.get('price', 0) / 100000,
                            'available': item_data.get('stock', 0) > 0
                        }
            
        except Exception as e:
            print(f"   ❌ HTML scraping failed: {e}")
        
        return None
    
    def check_product(self, shop_id, item_id):
        """Try multiple methods to get product info"""
        
        # Try Method 1: Standard API
        try:
            print(f"   🌐 Method 1: Standard API...")
            url = "https://shopee.co.id/api/v4/item/get"
            params = {'shopid': shop_id, 'itemid': item_id}
            headers = self.get_browser_headers()
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            print(f"   📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    item = data['data']
                    return {
                        'name': item.get('name', 'Unknown'),
                        'stock': item.get('stock', 0),
                        'price': item.get('price', 0) / 100000,
                        'available': item.get('stock', 0) > 0
                    }
        except:
            pass
        
        # Try Method 2: PC API
        result = self.check_product_web_scraping(shop_id, item_id)
        if result:
            return result
        
        # Try Method 3: Mobile API
        result = self.check_product_mobile_api(shop_id, item_id)
        if result:
            return result
        
        # Try Method 4: HTML Scraping
        result = self.check_product_html_scrape(shop_id, item_id)
        if result:
            return result
        
        print(f"   ❌ All methods failed")
        return None
    
    def monitor(self, products):
        """Monitor produk dan kirim notifikasi jika ada perubahan"""
        print(f"🤖 GitHub Actions - Shopee Monitor v3.0")
        print(f"⏰ Runtime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("=" * 60)
        
        state = self.load_state()
        print(f"📂 Previous state: {state}")
        
        new_state = {}
        
        for idx, product in enumerate(products, 1):
            shop_id = product['shop_id']
            item_id = product['item_id']
            product_key = f"{shop_id}_{item_id}"
            
            print(f"\n🔍 [{idx}/{len(products)}] Checking: {product_key}")
            
            info = self.check_product(shop_id, item_id)
            
            if info:
                current_status = info['available']
                previous_status = state.get(product_key)
                
                print(f"\n   ✅ Product found!")
                print(f"   📦 {info['name']}")
                print(f"   💰 Rp {info['price']:,.0f}")
                print(f"   📊 Stock: {info['stock']}")
                print(f"   {'✅ READY' if current_status else '❌ OUT OF STOCK'}")
                
                # Send notification if status changed
                if previous_status is not None and previous_status != current_status:
                    print(f"\n   🚨 STATUS CHANGED!")
                    
                    message = (
                        f"{'✅' if current_status else '❌'} <b>{'PRODUK READY!' if current_status else 'PRODUK HABIS!'}</b>\n\n"
                        f"📦 <b>{info['name']}</b>\n"
                        f"💰 Rp {info['price']:,.0f}\n"
                        f"📊 {info['stock']} unit\n"
                        f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                        f"🔗 <a href='https://shopee.co.id/product/{shop_id}/{item_id}'>Lihat Produk</a>"
                    )
                    
                    self.send_telegram(message)
                
                new_state[product_key] = current_status
            else:
                print(f"   ⚠️  Failed to get info, keeping old state")
                if product_key in state:
                    new_state[product_key] = state[product_key]
            
            time.sleep(3)  # Delay between products
        
        self.save_state(new_state)
        
        print("\n" + "=" * 60)
        print("✅ Monitoring completed!")
        print("=" * 60)


if __name__ == "__main__":
    print("🚀 SHOPEE TELEGRAM MONITOR - GITHUB ACTIONS")
    print("=" * 60)
    
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    print(f"🔐 Secrets: {'✅' if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID else '❌'}")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Missing credentials!")
        exit(1)
    
    PRODUCTS = [
        {
            'shop_id': '581472460',
            'item_id': '28841260015'
        }
    ]
    
    print(f"📦 Monitoring {len(PRODUCTS)} product(s)\n")
    
    bot = ShopeeMonitor(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    bot.monitor(PRODUCTS)
