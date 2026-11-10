import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "9072636852:AAF-oWOqZrdRW7jWgDvZIt2sD2LxP8PO6uI")

# Admin Telegram IDs (can be multiple, comma-separated e.g. "12345678,87654321")
raw_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in raw_admin_ids.split(",") if i.strip().isdigit()]

# Currency settings
CURRENCY = os.getenv("CURRENCY", "$")

# Support contact link or username (e.g. "@username" or "https://t.me/yourusername")
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@support")

# KHQR / Bakong Payment Settings (https://www.lorndavid.online/docs)
BAKONG_GATEWAY_URL = os.getenv("BAKONG_GATEWAY_URL", "https://lorndavid.online")
BAKONG_ACCOUNT_ID = os.getenv("BAKONG_ACCOUNT_ID", "kem_poch@aclb")
BAKONG_MERCHANT_NAME = os.getenv("BAKONG_MERCHANT_NAME", "KEM POCH")
BAKONG_MERCHANT_CITY = os.getenv("BAKONG_MERCHANT_CITY", "PHNOM PENH")
BAKONG_CURRENCY = os.getenv("BAKONG_CURRENCY", "USD")
BAKONG_API_TOKEN = os.getenv("BAKONG_API_TOKEN", "")

# Payment instructions shown when user clicks "Deposit"
PAYMENT_INFO = os.getenv("PAYMENT_INFO", """
💳 *How to Top Up Your Balance:*

1. Choose a payment method:
   • *Crypto (USDT TRC20):* `Txxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   • *Bank Transfer / PayPal / Binance:* Contact Admin
2. After making payment, send screenshot & your Telegram ID (`{user_id}`) to Admin: {support_contact}
3. Your balance will be credited within a few minutes!
""")
