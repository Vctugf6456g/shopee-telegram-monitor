import requests
import time
import logging

# Setting up logging
logging.basicConfig(level=logging.INFO)

class ShopeeMonitor:
    def __init__(self):
        self.features_active = ["priority alerts", "checkout links", "stock urgency"]

    def display_startup_message(self):
        logging.info("Features Active: ")
        for feature in self.features_active:
            logging.info(f"- {feature}")

    def monitor_once(self):
        logging.info("Monitoring once...")
        # Logic to check for updates in stock and checkout links

    def run_continuous(self):
        while True:
            self.monitor_once()
            time.sleep(60)  # wait 60 seconds before checking again

if __name__ == '__main__':
    monitor = ShopeeMonitor()
    monitor.display_startup_message()
    monitor.run_continuous()