import requests
import os
import json
from datetime import datetime
import time
import traceback

class ShopeeMonitor:
    def __init__(self, shop_id, item_id, check_interval=300):
        self.shop_id = shop_id
        self.item_id = item_id
        self.check_interval = check_interval
        self.base_url = "https://shopee.co.id/api/v4/"
    
    def get_wib_time(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def load_state(self):
        try:
            with open('state.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_state(self, state):
        with open('state.json', 'w') as f:
            json.dump(state, f)

    def send_telegram(self, message):
        telegram_token = os.getenv('TELEGRAM_TOKEN')
        chat_id = os.getenv('CHAT_ID')
        if telegram_token and chat_id:
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {'chat_id': chat_id, 'text': message}
            requests.post(url, json=payload)

    def check_product(self):
        try:
            # Method 1: Standard API
            response = requests.get(f"{self.base_url}item/get", params={"shop_id": self.shop_id, "item_id": self.item_id})
            response.raise_for_status()
            data = response.json()
            if data and 'data' in data:
                return data['data']
        except Exception as e:
            traceback.print_exc()  # Log the error for debugging

        try:
            # Method 2: PC API
            response = requests.get(f"{self.base_url}pdp/get_pc", params={"shop_id": self.shop_id, "item_id": self.item_id})
            response.raise_for_status()
            data = response.json()
            if data and 'data' in data:
                return data['data']
        except Exception as e:
            traceback.print_exc()  # Log the error for debugging

        return None

    def monitor_once(self):
        product_data = self.check_product()
        if product_data:
            self.send_telegram(f"Product data: {product_data}")

    def run_continuous(self):
        while True:
            self.monitor_once()
            time.sleep(self.check_interval)

if __name__ == "__main__":
    shop_id = 581472460
    item_id = 28841260015
    CHECK_INTERVAL = 300
    
    if os.getenv('TELEGRAM_TOKEN') and os.getenv('CHAT_ID'):
        monitor = ShopeeMonitor(shop_id, item_id, CHECK_INTERVAL)
        monitor.run_continuous()
    else:
        print("Environment variables TELEGRAM_TOKEN and CHAT_ID must be set.")