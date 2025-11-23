import requests
import os
import json
from datetime import datetime
import traceback

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
            traceback.print_exc()
            return None
    
    def check_product(self, shop_id, item_id):
        """Cek status produk Shopee"""
        try:
            url = "https://shopee.co.id/api/v4/item/get"
            params = {
                'shopid': shop_id,
                'itemid': item_id
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://shopee.co.id/',
                'Accept': 'application/json',
                'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            
            print(f"   🌐 Requesting Shopee API...")
            print(f"   URL: {url}")
            print(f"   Params: {params}")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            print(f"   📡 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Debug: Print raw response
                print(f"   📄 Response keys: {list(data.keys())}")
                
                if 'data' in data and data['data']:
                    item = data['data']
                    
                    # Debug: Print item keys
                    print(f"   🔑 Item keys: {list(item.keys())[:10]}...")
                    
                    product_name = item.get('name', 'Unknown Product')
                    stock = item.get('stock', 0)
                    price = item.get('price', 0) / 100000
                    
                    result = {
                        'name': product_name,
                        'stock': stock,
                        'price': price,
                        'available': stock > 0
                    }
                    
                    print(f"   ✅ Product data retrieved successfully")
                    return result
                    
                elif 'error' in data:
                    print(f"   ❌ Shopee API error: {data.get('error')}")
                    print(f"   Error message: {data.get('error_msg', 'No message')}")
                else:
                    print(f"   ⚠️  No 'data' field in response")
                    print(f"   Raw response: {json.dumps(data, indent=2)[:500]}")
                    
            else:
                print(f"   ❌ HTTP Error {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Request timeout")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            traceback.print_exc()
            
        return None
    
    def monitor(self, products):
        """Monitor produk dan kirim notifikasi jika ada perubahan"""
        print(f"🤖 GitHub Actions - Shopee Monitor v2.0")
        print(f"⏰ Runtime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"📍 Timezone: UTC+0")
        print("=" * 60)
        
        # Load previous state
        state = self.load_state()
        print(f"📂 Previous state: {state}")
        
        new_state = {}
        
        for idx, product in enumerate(products, 1):
            shop_id = product['shop_id']
            item_id = product['item_id']
            product_key = f"{shop_id}_{item_id}"
            
            print(f"\n🔍 [{idx}/{len(products)}] Checking product: {product_key}")
            print(f"   Shop ID: {shop_id}")
            print(f"   Item ID: {item_id}")
            
            # Check product
            info = self.check_product(shop_id, item_id)
            
            if info:
                current_status = info['available']
                previous_status = state.get(product_key)
                
                print(f"\n   📦 Name: {info['name']}")
                print(f"   💰 Price: Rp {info['price']:,.0f}")
                print(f"   📊 Stock: {info['stock']} units")
                print(f"   {'✅ READY' if current_status else '❌ OUT OF STOCK'}")
                print(f"   🔄 Previous status: {previous_status}")
                print(f"   🔄 Current status: {current_status}")
                
                # Send notification if status changed
                if previous_status is not None and previous_status != current_status:
                    print(f"\n   🚨 STATUS CHANGED! Sending notification...")
                    
                    if current_status:
                        emoji = "✅"
                        status_text = "PRODUK READY!"
                        stock_text = f"{info['stock']} unit"
                    else:
                        emoji = "❌"
                        status_text = "PRODUK HABIS!"
                        stock_text = "0 unit"
                    
                    message = (
                        f"{emoji} <b>{status_text}</b>\n\n"
                        f"📦 <b>{info['name']}</b>\n"
                        f"💰 Harga: Rp {info['price']:,.0f}\n"
                        f"📊 Stok: {stock_text}\n"
                        f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                        f"🔗 <a href='https://shopee.co.id/product/{shop_id}/{item_id}'>{'BELI SEKARANG!' if current_status else 'Lihat Produk'}</a>"
                    )
                    
                    self.send_telegram(message)
                    
                elif previous_status is None:
                    print(f"   ℹ️  First time checking, no notification sent")
                    print(f"   💡 Next check will compare with current status")
                else:
                    print(f"   ℹ️  No status change, no notification needed")
                
                # Update state
                new_state[product_key] = current_status
                
            else:
                print(f"   ❌ Failed to get product info")
                # Keep previous state if failed
                if product_key in state:
                    new_state[product_key] = state[product_key]
        
        # Save new state
        print(f"\n💾 Saving new state...")
        self.save_state(new_state)
        
        print("\n" + "=" * 60)
        print("✅ Monitoring completed!")
        print(f"📊 Checked {len(products)} product(s)")
        print(f"⏰ Next check: ~5 minutes (GitHub Actions schedule)")
        print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SHOPEE TELEGRAM MONITOR - GITHUB ACTIONS")
    print("=" * 60)
    
    # Get from environment variables (GitHub Secrets)
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    print(f"\n🔐 Checking environment variables...")
    print(f"   TELEGRAM_BOT_TOKEN: {'✅ Set' if TELEGRAM_BOT_TOKEN else '❌ Missing'}")
    print(f"   TELEGRAM_CHAT_ID: {'✅ Set' if TELEGRAM_CHAT_ID else '❌ Missing'}")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n❌ ERROR: Environment variables not found!")
        print("   Please check GitHub Secrets configuration")
        exit(1)
    
    # Products to monitor
    PRODUCTS = [
        {
            'shop_id': '581472460',
            'item_id': '28841260015'
        }
    ]
    
    print(f"\n📋 Configuration:")
    print(f"   Products to monitor: {len(PRODUCTS)}")
    print(f"   Product: Suno AI Pro Plan")
    print(f"   Shop ID: {PRODUCTS[0]['shop_id']}")
    print(f"   Item ID: {PRODUCTS[0]['item_id']}")
    print()
    
    # Run monitor
    bot = ShopeeMonitor(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    bot.monitor(PRODUCTS)
