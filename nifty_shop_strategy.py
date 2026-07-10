"""
Converse India Size Monitor - Telegram Bot
Monitors Wave Motion Trainer (A19128C-Black) for UK Size 9 availability.
"""

import os
import json
import requests
import schedule
import time
import logging
import random
from datetime import datetime

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID    = os.environ.get("CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "360"))
# ──────────────────────────────────────────────────────────────────────────────

PRODUCT_URL       = "https://www.converse.in/converse-wave-motion-trainer-a19128c-black.html"
PRODUCT_NAME      = "Converse Wave Motion Trainer (Black)"
URL_KEY           = "converse-wave-motion-trainer-a19128c-black"
TARGET_SIZE_LABEL = "9 UK"
TARGET_VALUE_INDEX = 226   # hardcoded from API response

GRAPHQL_URL = "https://www.converse.in/graphql"

GRAPHQL_QUERY = """query getProductDetailForProductPage($urlKey: String!) {
  products(filter: {url_key: {eq: $urlKey}}) {
    items {
      name
      ... on ConfigurableProduct {
        variants {
          attributes { code value_index }
          product {
            sku
            stock_status
          }
        }
      }
    }
  }
}"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

_last_notified_available = None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]

def fetch_size_status():
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "en-IN,en;q=0.9",
        "Content-Type": "application/json",
        "Referer": PRODUCT_URL,
        "store": "default",
    }
    payload = {
        "query": GRAPHQL_QUERY,
        "operationName": "getProductDetailForProductPage",
        "variables": {"urlKey": URL_KEY}
    }
    try:
        log.info("Querying Converse India GraphQL API...")
        r = requests.post(GRAPHQL_URL, json=payload, headers=headers, timeout=20)
        log.info("Status: " + str(r.status_code) + " | Length: " + str(len(r.text)))
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.error("GraphQL fetch failed: " + str(e))
    return None

def check_uk9_availability(data):
    if not data:
        return False, "no data"
    try:
        items = data["data"]["products"]["items"]
        if not items:
            return False, "no items"

        variants = items[0].get("variants", [])

        for variant in variants:
            for attr in variant.get("attributes", []):
                if attr.get("code") == "size" and attr.get("value_index") == TARGET_VALUE_INDEX:
                    stock = variant["product"]["stock_status"]
                    sku = variant["product"]["sku"]
                    log.info("UK9 variant found | SKU: " + sku + " | stock_status: " + stock)
                    return stock == "IN_STOCK", "stock_status=" + stock

        return False, "UK9 variant not found"

    except Exception as e:
        log.error("Parse error: " + str(e))
        return False, "parse error: " + str(e)

def send_telegram(message):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        }, timeout=10)
        r.raise_for_status()
        log.info("Telegram sent.")
    except Exception as e:
        log.error("Telegram error: " + str(e))

def check_size_availability():
    global _last_notified_available

    log.info("Checking UK9 for " + PRODUCT_NAME + "...")
    data = fetch_size_status()

    if not data:
        log.warning("No data returned, will retry next interval.")
        return

    available, reason = check_uk9_availability(data)
    log.info("UK9 available: " + str(available) + " | Reason: " + reason)

    if available and _last_notified_available is not True:
        msg = (
            "UK SIZE 9 IS NOW AVAILABLE!\n\n"
            + PRODUCT_NAME + "\n"
            "Buy now: " + PRODUCT_URL + "\n\n"
            "Checked at: " + datetime.now().strftime("%d %b %Y %I:%M %p")
        )
        send_telegram(msg)
        _last_notified_available = True

    elif not available and _last_notified_available is True:
        send_telegram("UK Size 9 no longer available for " + PRODUCT_NAME + "\nWill notify when it is back!")
        _last_notified_available = False
    else:
        log.info("No state change, skipping notification.")

def main():
    log.info("==================================================")
    log.info("Converse Size Monitor started")
    log.info("Product: " + PRODUCT_NAME)
    log.info("Target: " + TARGET_SIZE_LABEL)
    log.info("Interval: every " + str(CHECK_INTERVAL_MINUTES) + " minutes")
    log.info("==================================================")
    send_telegram(
        "Converse Size Monitor started!\n"
        "Watching: " + PRODUCT_NAME + "\n"
        "Size: 9 UK\n"
        "Checking every " + str(CHECK_INTERVAL_MINUTES) + " minutes."
    )
    check_size_availability()
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_size_availability)
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
