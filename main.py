import os
import time
import requests
import telebot
from datetime import datetime
import pytz

# Constants
SHOP_ID = "581472460"
ITEM_ID = "28841260015"
CHECK_INTERVAL = 300  # 5 minutes
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ALERT_PRIORITY = 3  # number of notifications to send on priority

# Configure Telegram bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Function to send notification
def send_notification(message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        print(f"[{current_time()}] Notification sent: {message}")
    except Exception as e:
        print(f"Failed to send notification: {e}")

# Check product availability via Shopee APIs
def check_product():
    try:
        # Define the API endpoints
        standard_api_url = f"https://shopee.com/api/v2/product/{SHOP_ID}/{ITEM_ID}"
        pc_api_url = f"https://shopee.com/api/v2/pc/product/{SHOP_ID}/{ITEM_ID}"

        # Standard API request
        response = requests.get(standard_api_url)
        response.raise_for_status()
        product_info = response.json()
        
        # Check stock and availability
        stock = product_info['data']['stock']
        if stock > 0:
            urgent_message = f"Item ID {ITEM_ID} is in stock! Checkout link: https://shopee.com/product/{SHOP_ID}/{ITEM_ID}"
            send_notification(urgent_message)

        # Additional checks can be implemented with the PC API
        response = requests.get(pc_api_url)
        response.raise_for_status()

    except Exception as e:
        print(f"Error checking product: {e}")

# Helper function to get current time in WIB
def current_time():
    wib_timezone = pytz.timezone('Asia/Jakarta')
    return datetime.now(wib_timezone).strftime('%Y-%m-%d %H:%M:%S')

# Main loop to monitor the product
def main():
    print(f"[{current_time()}] Bot started. Monitoring item...")
    while True:
        check_product()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()