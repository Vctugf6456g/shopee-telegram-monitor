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
        self.telegram_api = f'https://api.telegram.org/bot{telegram_bot_token}'
        self.state_file = 'product_state.json'
        
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
            print(f'⚠️  Load state warning: {e}')
        return {}
    
    def save_state(self, state):
        """Simpan status produk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            print(f'💾 State saved successfully')
        except Exception as e:
            print(f'❌ Error saving state: {e}')
    
    def send_telegram(self, message, disable_notification=False):
        """Kirim pesan ke Telegram"""
        try:
            url = f'{self.telegram_api}/sendMessage'
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False,
                'disable_notification': disable_notification
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f'✅ Telegram notification sent!')
                return True
            else:
                print(f'❌ Telegram error: {response.status_code}')
                return False
                
        except Exception as e:
            print(f'❌ Send error: {e}')
            return False
    
    def send_priority_alert(self, message):
        """Kirim notifikasi prioritas (3x berturut-turut)"""
        print(f'   🔔 Sending PRIORITY ALERT (3x notifications)...')
        
        for i in range(3):
            print(f'   📢 Alert #{i+1}/3')
            self.send_telegram(message, disable_notification=False)
            if i < 2:  # Don't sleep after last notification
                time.sleep(2)  # 2 second delay between notifications
        
        print(f'   ✅ Priority alert sent successfully!')
    
    def get_checkout_link(self, shop_id, item_id):
        """Generate direct checkout link"""
        # Shopee direct add to cart link
        return f'https://shopee.co.id/universal-link/now-golden/cart?itemId={item_id}&shopId={shop_id}'
    
    def get_product_link(self, shop_id, item_id):
        """Generate product page link"""
        return f'https://shopee.co.id/product/{shop_id}/{item_id}'
    
    def format_stock_alert(self, stock):
        """Format stock dengan urgency indicator"""
        if stock == 0:
            return '❌ HABIS'
        elif stock < 5:
            return f'🔥 TERBATAS! ({stock} unit)'
        elif stock < 10:
            return f'⚠️ {stock} unit tersisa'
        else:
            return f'✅ {stock} unit'
    
    def check_product(self, shop_id, item_id):
        """Cek produk Shopee dengan multiple methods"""
        
        # Method 1: Standard API
        try:
            print(f'   📡 Trying standard API...')
            
            url = 'https://shopee.co.id/api/v4/item/get'
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
            
            print(f'   Status: {response.status_code}')
            
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
                    
                    print(f'   ✅ Success!')
                    return result
                    
        except Exception as e:
            print(f'   ⚠️  Method 1 failed: {str(e)[:50]}')
        
        # Method 2: PC API
        try:
            print(f'   📡 Trying PC API...')
            
            url = 'https://shopee.co.id/api/v4/pdp/get_pc'
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
                    
                    print(f'   ✅ Success!')
                    return result
                    
        except Exception as e:
            print(f'   ⚠️  Method 2 failed: {str(e)[:50]}')
        
        print(f'   ❌ All methods failed')
        return None
    
    def monitor_once(self, products):
        """Single monitoring check"""
        wib_time = self.get_wib_time()
        
        print(f'\n{'='*60}')
        print(f'🤖 Shopee Monitor - Railway.app')
        print(f'⏰ {wib_time} WIB')
        print(f'{'='*60}\n')
        
        state = self.load_state()
        new_state = {}\n        for idx, product in enumerate(products, 1):\n            shop_id = product['shop_id']\n            item_id = product['item_id']\n            product_key = f'{shop_id}_{item_id}'\n            print(f'🔍 [{idx}/{len(products)}] Product: {product_key}')\n            info = self.check_product(shop_id, item_id)\n            if info: \n                current_status = info['available']\n                previous_status = state.get(product_key)\n                stock = info['stock']\n                stock_display = self.format_stock_alert(stock)\n                print(f'\n   📦 {info['name']}')\n                print(f'   💰 Rp {info['price']:,.0f}')\n                print(f'   📊 {stock_display}\n')\n                # Notify if changed\n                if previous_status is not None and previous_status != current_status: \n                    print(f'   🚨 STATUS CHANGED! Sending PRIORITY notification...')\n                    wib_time = self.get_wib_time()\n                    if current_status:  # PRODUK READY!\n                        # Urgency level\n                        if stock < 5: \n                            urgency = '🔥🔥🔥 STOK SANGAT TERBATAS! BELI SEKARANG! 🔥🔥🔥'\n                        elif stock < 10: \n                            urgency = '⚠️ STOK TERBATAS! CEPAT!'\n                        else: \n                            urgency = '✅ Stok Tersedia'\n                        checkout_link = self.get_checkout_link(shop_id, item_id)\n                        product_link = self.get_product_link(shop_id, item_id)\n                        message = (\n                            f'🚨🚨🚨 <b>PRODUK READY!</b> 🚨🚨🚨\n\n'\n                            f'{urgency}\n\n'\n                            f'📦 <b>{info['name']}</b>\n'\n                            f'💰 <b>Rp {info['price']:,.0f}</b>\n'\n                            f'📊 Stok: <b>{stock} unit</b>\n'\n                            f'🕐 {wib_time} WIB\n\n'\n                            f'⚡ <b>CHECKOUT SEKARANG:</b>\n'\n                            f'🛒 <a href='{checkout_link}'>LANGSUNG CHECKOUT!</a>\n\n'\n                            f'📱 <a href='{product_link}'>Lihat Detail Produk</a>\n\n'\n                            f'⏰ <b>JANGAN SAMPAI KEHABISAN!</b>'\n                        )\n                        # Send PRIORITY ALERT (3x notifications)\n                        self.send_priority_alert(message)\n                    else:  # PRODUK HABIS\n                        message = (\n                            f'❌ <b>PRODUK HABIS!</b>\n\n'\n                            f'📦 <b>{info['name']}</b>\n'\n                            f'💰 Rp {info['price']:,.0f}\n'\n                            f'📊 Stok: <b>0 unit</b>\n'\n                            f'🕐 {wib_time} WIB\n\n'\n                            f'⏳ Bot akan terus monitoring...'\n                        )\n                        self.send_telegram(message)\n                elif previous_status is None: \n                    print(f'   ℹ️  First check, baseline saved')\n                else:\n                    print(f'   ✓ No change')\n                new_state[product_key] = current_status\n            else: \n                print(f'   ❌ Failed to fetch')\n                if product_key in state:\n                    new_state[product_key] = state[product_key]\n            print()        \n        self.save_state(new_state)\n        print(f'{'='*60}\n')\n    
    def run_continuous(self, products, interval=300):\n        """Run monitoring continuously"""\n        print(f'🚀 Starting continuous monitoring...')\n        print(f'⏱️  Check interval: {interval} seconds ({interval//60} minutes)')\n        print(f'📦 Products: {len(products)}')\n        print()\n        # Send startup notification\n        wib_time = self.get_wib_time()\n        self.send_telegram(\n            "🤖 <b>Shopee Monitor Started!</b>\n\n"\n            f'✅ Railway.app deployment active\n'\n            f'📦 Monitoring {len(products)} product(s)\n'\n            f'⏱️  Interval: {interval//60} minutes\n'\n            f'🕐 {wib_time} WIB\n\n'\n            f'🔔 <b>Features Active:</b>\n'\n            f'⚡ Priority alerts (3x notification)\n'\n            f'🛒 Direct checkout links\n'\n            f'🔥 Stock urgency indicators\n'\n            f'📊 Real-time monitoring'\n        )\n        while True:\n            try:\n                self.monitor_once(products)\n                print(f'⏳ Waiting {interval} seconds until next check...')\n                print(f'⏰ Next check in {interval//60} minutes\n')\n                time.sleep(interval)\n            except KeyboardInterrupt:\n                print('\n🛑 Stopped by user')\n                wib_time = self.get_wib_time()\n                self.send_telegram(f'🛑 <b>Bot Stopped</b>\n\n🕐 {wib_time} WIB')\n                break\n            except Exception as e:\n                print(f'\n❌ Error: {e}')\n                traceback.print_exc()\n                print(f'\n⏳ Retrying in 60 seconds...\n')\n                time.sleep(60)\n

if __name__ == '__main__':\n    print('\n' + '='*60)\n    print('🚀 SHOPEE TELEGRAM MONITOR - RAILWAY')\n    print('='*60 + '\n')\n    # Get credentials\n    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')\n    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')\n    CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '300'))  # Default 5 minutes\n    # Validate\n    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:\n        print('❌ ERROR: Missing environment variables!')\n        print('   Required: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID')\n        exit(1)\n    print(f'✅ Credentials loaded')\n    print(f'⏱️  Interval: {CHECK_INTERVAL}s ({CHECK_INTERVAL//60}min)\n')\n    # Products to monitor\n    PRODUCTS = [\n        {\n            'shop_id': '581472460',\n            'item_id': '28841260015'\n        }\n    ]\n    # Run bot\n    bot = ShopeeMonitor(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)\n    bot.run_continuous(PRODUCTS, interval=CHECK_INTERVAL)\n