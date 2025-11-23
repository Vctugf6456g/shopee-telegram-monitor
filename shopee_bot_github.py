import requests
import os
import json
from datetime import datetime

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
        except:
            pass
        return {}
    
    def save_state(self, state):
        """Simpan status produk ke file"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f)
    
    def send_telegram(self, message):
        """Kirim pesan ke Telegram"""
        try:
            url = f"{self.telegram_api}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            print(f"❌ Error kirim pesan: {e}")
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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://shopee.co.id/'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    item = data['data']
                    return {
                        'name': item.get('name', 'Unknown'),
                        'stock': item.get('stock', 0),
                        'price': item.get('price', 0) / 100000,
                        'available': item.get('stock', 0) > 0
                    }
        except Exception as e:
            print(f"❌ Error cek produk: {e}")
        return None
    
    def monitor(self, products):
        """Monitor produk dan kirim notifikasi jika ada perubahan"""
        print(f"🤖 GitHub Actions - Shopee Monitor")
        print(f"⏰ Runtime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("=" * 60)
        
        state = self.load_state()
        
        for product in products:
            shop_id = product['shop_id']
            item_id = product['item_id']
            product_key = f"{shop_id}_{item_id}"
            
            print(f"\n🔍 Checking product: {product_key}")
            
            info = self.check_product(shop_id, item_id)
            
            if info:
                current_status = info['available']
                previous_status = state.get(product_key)
                
                print(f"   📦 {info['name']}")
                print(f"   💰 Rp {info['price']:,.0f}")
                print(f"   📊 Stock: {info['stock']}")
                print(f"   ✅ Status: {'READY' if current_status else 'HABIS'}")
                
                # Kirim notifikasi jika status berubah
                if previous_status is not None and previous_status != current_status:
                    if current_status:
                        message = (
                            f"✅ <b>PRODUK READY!</b>\n\n"
                            f"📦 <b>{info['name']}</b>\n"
                            f"💰 Harga: Rp {info['price']:,.0f}\n"
                            f"📊 Stok: {info['stock']} unit\n"
                            f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                            f"🔗 <a href='https://shopee.co.id/product/{shop_id}/{item_id}'>BELI SEKARANG!</a>"
                        )
                    else:
                        message = (
                            f"❌ <b>PRODUK HABIS!</b>\n\n"
                            f"📦 <b>{info['name']}</b>\n"
                            f"💰 Harga: Rp {info['price']:,.0f}\n"
                            f"📊 Stok: 0 unit\n"
                            f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                            f"⏳ Bot akan notifikasi saat ready kembali."
                        )
                    
                    print(f"   📤 Sending notification...")
                    result = self.send_telegram(message)
                    if result:
                        print(f"   ✅ Notification sent!")
                
                # Update state
                state[product_key] = current_status
        
        # Simpan state
        self.save_state(state)
        print("\n" + "=" * 60)
        print("✅ Monitoring completed!")


if __name__ == "__main__":
    # Ambil dari environment variables (GitHub Secrets)
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID tidak ditemukan!")
        print("   Pastikan sudah setup GitHub Secrets")
        exit(1)
    
    # Produk yang dipantau: Suno AI Pro Plan
    PRODUCTS = [
        {
            'shop_id': '581472460',
            'item_id': '28841260015'
        }
    ]
    
    bot = ShopeeMonitor(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    bot.monitor(PRODUCTS)
