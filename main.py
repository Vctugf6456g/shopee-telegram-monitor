import requests
import os
import json
from datetime import datetime, timedelta
import time
import traceback


class ShopeeMonitor:
    def __init__(self, shop_id, item_id, telegram_bot_token, telegram_chat_id, check_interval=300):
        self.shop_id = shop_id
        self.item_id = item_id
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.check_interval = check_interval
        self.state = self.load_state()

    def get_wib_time(self):
        return datetime.utcnow() + timedelta(hours=7)

    def load_state(self):
        try:
            with open('state.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'last checked': None, 'last status': None}

    def save_state(self):
        with open('state.json', 'w') as f:
            json.dump(self.state, f)

    def send_telegram(self, message):
        url = f'https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage'
        params = {'chat_id': self.telegram_chat_id, 'text': message}
        requests.get(url, params=params)

    def send_priority_alert(self, message):
        for _ in range(3):  # send 3 notifications
            self.send_telegram(message)
            time.sleep(1)  # sleep for a second between alerts

    def get_checkout_link(self):
        return f'https://shopee.com/{self.shop_id}/{self.item_id}'

    def get_product_link(self):
        return f'https://shopee.com/product/{self.shop_id}/{self.item_id}'

    def format_stock_alert(self, status):
        return f'Stock status for item {self.item_id} is: {status}'

    def check_product(self):
        url = f'https://shopee.co.id/api/v2/product/get_details?shopid={self.shop_id}&itemid={self.item_id}'
        response = requests.get(url)
        data = response.json()
        return data['data']['item']['stock'] > 0

    def monitor_once(self):
        current_time = self.get_wib_time()
        product_available = self.check_product()
        message = self.format_stock_alert(product_available)

        if product_available and (self.state['last status'] != 'available'):
            self.send_priority_alert(message)
        elif not product_available and (self.state['last status'] != 'unavailable'):
            self.send_telegram(message)

        self.state['last checked'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
        self.state['last status'] = 'available' if product_available else 'unavailable'
        self.save_state()

    def run_continuous(self):
        while True:
            self.monitor_once()
            time.sleep(self.check_interval)


if __name__ == '__main__':
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))
    monitor = ShopeeMonitor(581472460, 28841260015, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CHECK_INTERVAL)
    monitor.run_continuous()