import logging
import sys
import time
import threading

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import telebot
from telebot import types
import config
import database
import keyboards
import khqr_service

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Bot
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

# /start command
@bot.message_handler(commands=["start"])
def handle_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "Customer"

    user = database.get_or_create_user(user_id, username, first_name)
    admin_status = is_admin(user_id)

    welcome_text = (
        f"👋 <b>Welcome, {first_name}!</b>\n\n"
        f"🏪 <b>ICbuy - Instant Account Store</b>\n"
        f"Buy high-quality, verified <b>Gmail, Facebook</b>, and other social accounts instantly.\n\n"
        f"👤 <b>Your ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Your Balance:</b> <code>{config.CURRENCY}{user['balance']:.2f}</code>\n\n"
        f"👇 Select an option below to get started:"
    )

    # Send persistent reply keyboard
    bot.send_message(
        chat_id=message.chat.id,
        text="Choose an action from the menu below:",
        reply_markup=keyboards.main_reply_keyboard(is_admin=admin_status)
    )

    # Send interactive inline menu
    bot.send_message(
        chat_id=message.chat.id,
        text=welcome_text,
        reply_markup=keyboards.main_inline_menu(is_admin=admin_status)
    )

# /id command
@bot.message_handler(commands=["id"])
def handle_id(message: types.Message):
    user_id = message.from_user.id
    bot.reply_to(
        message, 
        f"🆔 Your Telegram ID is: <code>{user_id}</code>\n\n"
        f"<i>(Share this ID with Admin to top up your balance, or add it to ADMIN_IDS in .env to become admin)</i>"
    )

# Handle text buttons from reply keyboard
@bot.message_handler(func=lambda msg: msg.text in [
    "🛒 Buy Accounts", "💰 My Balance / Deposit", "📜 My Orders", "ℹ️ Support", "⚙️ Admin Panel"
])
def handle_reply_buttons(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    admin_status = is_admin(user_id)

    if text == "🛒 Buy Accounts":
        show_categories(message.chat.id)
    elif text == "💰 My Balance / Deposit":
        show_balance(message.chat.id, user_id)
    elif text == "📜 My Orders":
        show_orders(message.chat.id, user_id)
    elif text == "ℹ️ Support":
        show_support(message.chat.id)
    elif text == "⚙️ Admin Panel":
        if admin_status:
            show_admin_panel(message.chat.id)
        else:
            bot.send_message(message.chat.id, "⛔ Access denied. You are not an admin.")

# /admin command
@bot.message_handler(commands=["admin"])
def handle_admin_command(message: types.Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Access denied. Your user ID is not registered as an Admin.")
        return
    show_admin_panel(message.chat.id)

# Admin: /addbalance <user_id> <amount>
@bot.message_handler(commands=["addbalance"])
def handle_add_balance(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.strip().split()
    if len(parts) != 3:
        bot.reply_to(message, "⚠️ Usage: <code>/addbalance &lt;user_id&gt; &lt;amount&gt;</code>\nExample: <code>/addbalance 123456789 10.00</code>")
        return
    
    try:
        target_uid = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        bot.reply_to(message, "❌ Invalid user_id or amount. Both must be numeric.")
        return
    
    user = database.get_user(target_uid)
    if not user:
        bot.reply_to(message, f"❌ User ID <code>{target_uid}</code> not found in database. User must /start the bot first.")
        return
    
    new_bal = database.update_balance(target_uid, amount)
    bot.reply_to(
        message, 
        f"✅ Successfully credited <b>{config.CURRENCY}{amount:.2f}</b> to user <code>{target_uid}</code>!\n"
        f"💰 New balance: <b>{config.CURRENCY}{new_bal:.2f}</b>"
    )

    # Notify customer
    try:
        bot.send_message(
            target_uid,
            f"🎉 <b>Balance Credited!</b>\n\n"
            f"Amount: <b>+{config.CURRENCY}{amount:.2f}</b>\n"
            f"New Balance: <b>{config.CURRENCY}{new_bal:.2f}</b>\n\n"
            f"You can now purchase accounts with your balance!"
        )
    except Exception as e:
        logger.warning(f"Could not notify user {target_uid}: {e}")

# Admin: /setbakong <account_id>
@bot.message_handler(commands=["setbakong"])
def handle_set_bakong(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(
            message,
            f"⚠️ Usage: <code>/setbakong &lt;account_id&gt;</code>\n"
            f"Example: <code>/setbakong yourname@aba</code>\n"
            f"Current: <code>{config.BAKONG_ACCOUNT_ID}</code>"
        )
        return
    config.BAKONG_ACCOUNT_ID = parts[1].strip()
    bot.reply_to(message, f"✅ Bakong Account ID updated to: <code>{config.BAKONG_ACCOUNT_ID}</code>")

# Admin: /setbakongtoken <token>
@bot.message_handler(commands=["setbakongtoken"])
def handle_set_bakong_token(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2:
        bot.reply_to(
            message,
            "⚠️ Usage: <code>/setbakongtoken &lt;token&gt;</code>\n\n"
            "This token enables zero-click automated payment verification via NBC Bakong Open API."
        )
        return
    config.BAKONG_API_TOKEN = parts[1].strip()
    bot.reply_to(message, "✅ Bakong Open API Token updated successfully! Auto-payment is now active.")

# Admin: /checkgateway or /bakongstatus
@bot.message_handler(commands=["checkgateway", "bakongstatus"])
def handle_check_gateway(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    bot.send_chat_action(message.chat.id, "typing")
    health = khqr_service.check_gateway_health(getattr(config, "BAKONG_GATEWAY_URL", "https://lorndavid.online"))
    if health.get("online"):
        text = (
            f"🟢 <b>Bakong Gateway Status: Operational</b>\n\n"
            f"🌐 <b>Gateway:</b> {getattr(config, 'BAKONG_GATEWAY_URL', 'https://lorndavid.online')}\n"
            f"🏦 <b>Configured Account:</b> <code>{config.BAKONG_ACCOUNT_ID}</code>\n"
            f"👤 <b>Merchant:</b> {config.BAKONG_MERCHANT_NAME}\n"
            f"💵 <b>Currency:</b> {config.BAKONG_CURRENCY}\n"
            f"⚡ <b>NBC Real-Time Settlement:</b> Active"
        )
    else:
        text = (
            f"🔴 <b>Bakong Gateway Status: Unreachable</b>\n\n"
            f"🌐 <b>Gateway:</b> {getattr(config, 'BAKONG_GATEWAY_URL', 'https://lorndavid.online')}\n"
            f"⚠️ <b>Status:</b> {health.get('status') or health.get('error')}\n\n"
            f"<i>Local BakongKHQR engine will automatically handle generation.</i>"
        )
    bot.reply_to(message, text)

# Background Auto-Payment Poller
def auto_check_worker(dep_id: int, user_id: int, amount: float, md5_hash: str, chat_id: int, msg_id: int):
    """
    Periodically checks the Bakong API in the background (every 2.5s according to LuyRiel docs).
    When payment lands, credits user balance automatically without user sending image.
    """
    for _ in range(240):  # Check for up to 10 minutes (every 2.5 seconds)
        time.sleep(2.5)
        dep = database.get_deposit_request(dep_id)
        if not dep or dep["status"] in ["approved", "rejected"]:
            break
        
        res = khqr_service.check_bakong_transaction(md5_hash, getattr(config, "BAKONG_API_TOKEN", ""))
        if res.get("paid"):
            success, new_bal, target_uid, _ = database.approve_deposit(dep_id)
            if success:
                try:
                    bot.edit_message_caption(
                        f"✅ <b>PAYMENT CONFIRMED!</b>\n\n"
                        f"💵 Amount Paid: <b>+${amount:.2f} {config.BAKONG_CURRENCY}</b>\n"
                        f"🔢 Invoice: <code>#DEP-{dep_id}</code>\n"
                        f"⚡ Status: <b>Verified Automatically via NBC Bakong</b>",
                        chat_id,
                        msg_id
                    )
                except Exception:
                    pass
                
                try:
                    bot.send_message(
                        user_id,
                        f"🎉 <b>Payment Received Automatically!</b>\n\n"
                        f"Amount Credited: <b>+${amount:.2f} {config.BAKONG_CURRENCY}</b>\n"
                        f"💰 <b>New Wallet Balance:</b> <code>${new_bal:.2f}</code>\n\n"
                        f"Your balance is ready! You can now buy accounts.",
                        reply_markup=keyboards.main_reply_keyboard(is_admin=is_admin(user_id))
                    )
                except Exception as e:
                    logger.error(f"Failed notifying user {user_id}: {e}")

                for admin_id in config.ADMIN_IDS:
                    try:
                        bot.send_message(
                            admin_id,
                            f"🔔 <b>Automated KHQR Payment Received!</b>\n\n"
                            f"👤 Customer: <code>{user_id}</code>\n"
                            f"💵 Amount: <b>${amount:.2f} {config.BAKONG_CURRENCY}</b>\n"
                            f"🔢 Invoice: <code>#DEP-{dep_id}</code>\n"
                            f"⚡ Verified: <b>NBC Bakong Ledger (Automatic)</b>"
                        )
                    except Exception:
                        pass
                break

# KHQR Invoice Generation
def send_khqr_invoice(chat_id: int, user_id: int, amount: float):
    try:
        bill_no = f"DEP{int(time.time()) % 100000}"
        khqr_res = khqr_service.generate_khqr_data(
            account_id=config.BAKONG_ACCOUNT_ID,
            merchant_name=config.BAKONG_MERCHANT_NAME,
            amount=amount,
            currency=config.BAKONG_CURRENCY,
            bill_number=bill_no
        )
        qr_string = khqr_res["qr"]
        md5_hash = khqr_res.get("md5", "")
        deeplink = khqr_res.get("deeplink", "")

        dep_id = database.create_deposit_request(
            user_id=user_id,
            amount=amount,
            currency=config.BAKONG_CURRENCY,
            qr_string=qr_string,
            md5=md5_hash
        )

        amount_str = f"${amount:.2f} {config.BAKONG_CURRENCY}"
        img_buf = khqr_service.create_khqr_card(
            qr_string=qr_string,
            amount_str=amount_str,
            merchant_name=config.BAKONG_MERCHANT_NAME,
            account_id=config.BAKONG_ACCOUNT_ID
        )

        caption = (
            f"🇰🇭 <b>KHQR Automatic Payment #{dep_id}</b>\n\n"
            f"💵 <b>Amount to Pay:</b> <code>${amount:.2f} {config.BAKONG_CURRENCY}</code>\n"
            f"👤 <b>Receiver:</b> {config.BAKONG_MERCHANT_NAME}\n"
            f"🏦 <b>Bakong Account:</b> <code>{config.BAKONG_ACCOUNT_ID}</code>\n"
            f"🔢 <b>Reference:</b> <code>#DEP-{dep_id}</code>\n\n"
            f"📱 <b>How to Pay:</b>\n"
            f"1. Tap <b>1-Tap Pay</b> below to open Bakong directly, OR scan with ACLEDA, ABA, Bakong, etc.\n"
            f"2. Confirm the exact transfer of <b>${amount:.2f}</b>.\n\n"
            f"⚡ <i>Real-time NBC settlement active! Payment is verified automatically without needing a receipt screenshot.</i>"
        )

        sent_msg = bot.send_photo(
            chat_id=chat_id,
            photo=img_buf,
            caption=caption,
            reply_markup=keyboards.khqr_payment_keyboard(dep_id, deeplink=deeplink)
        )

        # Start auto poller in background thread
        threading.Thread(
            target=auto_check_worker,
            args=(dep_id, user_id, amount, md5_hash, chat_id, sent_msg.message_id),
            daemon=True
        ).start()

    except Exception as e:
        logger.error(f"Error generating KHQR: {e}")
        bot.send_message(chat_id, f"❌ Failed to generate KHQR: {e}")

# Helper View Functions
def show_categories(chat_id: int, message_id: int = None):
    text = "📁 <b>Select Account Category:</b>\n\nChoose the platform of accounts you want to buy:"
    markup = keyboards.categories_keyboard()
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

def show_balance(chat_id: int, user_id: int, message_id: int = None):
    user = database.get_user(user_id)
    bal = user["balance"] if user else 0.0
    text = (
        f"💰 <b>Your Wallet Balance:</b>\n\n"
        f"💵 <b>Current Balance:</b> <code>{config.CURRENCY}{bal:.2f}</code>\n"
        f"👤 <b>Account ID:</b> <code>{user_id}</code>\n\n"
        f"Need more balance? Click <b>How to Deposit</b> below to top up."
    )
    markup = keyboards.balance_keyboard()
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

def show_orders(chat_id: int, user_id: int, message_id: int = None):
    orders = database.get_user_orders(user_id, limit=8)
    if not orders:
        text = "📜 <b>Your Order History:</b>\n\nYou haven't purchased any accounts yet."
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 Browse Accounts", callback_data="menu:categories"))
        markup.add(types.InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:main"))
    else:
        text = "📜 <b>Your Recent Orders:</b>\n\nTap an order to view purchased account details:"
        markup = keyboards.orders_keyboard(orders)

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

def show_support(chat_id: int, message_id: int = None):
    text = (
        f"ℹ️ <b>Customer Support & Warranty:</b>\n\n"
        f"• All accounts are verified prior to listing.\n"
        f"• Instant delivery immediately after purchase.\n"
        f"• Replacement guarantee within 24 hours if credentials invalid on first login.\n\n"
        f"💬 <b>Support Contact:</b> {config.SUPPORT_CONTACT}\n"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Contact Support", url=f"https://t.me/{config.SUPPORT_CONTACT.lstrip('@')}"))
    markup.add(types.InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:main"))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

def show_admin_panel(chat_id: int, message_id: int = None):
    stats = database.get_stats()
    text = (
        f"⚙️ <b>Admin Control Panel</b>\n\n"
        f"👥 <b>Total Users:</b> {stats['user_count']}\n"
        f"📦 <b>Available Stock:</b> {stats['stock_available']}\n"
        f"🛒 <b>Accounts Sold:</b> {stats['sold_count']}\n"
        f"💵 <b>Total Revenue:</b> {config.CURRENCY}{stats['total_revenue']:.2f}\n\n"
        f"Select an admin tool below:"
    )
    markup = keyboards.admin_menu_keyboard()
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

# Callback Queries Handler
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: types.CallbackQuery):
    data = call.data
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    admin_status = is_admin(user_id)

    # 1. Main Navigation
    if data == "menu:main":
        user = database.get_or_create_user(user_id, call.from_user.username or "", call.from_user.first_name or "")
        welcome_text = (
            f"👋 <b>Welcome, {call.from_user.first_name or 'Customer'}!</b>\n\n"
            f"🏪 <b>ICbuy - Instant Account Store</b>\n"
            f"Buy high-quality, verified <b>Gmail, Facebook</b>, and other social accounts instantly.\n\n"
            f"👤 <b>Your ID:</b> <code>{user_id}</code>\n"
            f"💰 <b>Your Balance:</b> <code>{config.CURRENCY}{user['balance']:.2f}</code>\n\n"
            f"👇 Select an option below to get started:"
        )
        try:
            bot.edit_message_text(welcome_text, chat_id, msg_id, reply_markup=keyboards.main_inline_menu(is_admin=admin_status))
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif data == "menu:categories":
        show_categories(chat_id, msg_id)
        bot.answer_callback_query(call.id)

    elif data == "menu:balance":
        show_balance(chat_id, user_id, msg_id)
        bot.answer_callback_query(call.id)

    elif data == "menu:orders":
        show_orders(chat_id, user_id, msg_id)
        bot.answer_callback_query(call.id)

    elif data == "menu:support":
        show_support(chat_id, msg_id)
        bot.answer_callback_query(call.id)

    elif data == "menu:deposit_info":
        deposit_text = config.PAYMENT_INFO.format(
            user_id=user_id,
            support_contact=config.SUPPORT_CONTACT
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💬 Send Receipt to Admin", url=f"https://t.me/{config.SUPPORT_CONTACT.lstrip('@')}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back to Wallet", callback_data="menu:balance"))
        try:
            bot.edit_message_text(deposit_text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, deposit_text, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    # KHQR Deposit Flow
    elif data == "deposit:select_amount":
        text = (
            "🇰🇭 <b>KHQR Payment (Bakong / ABA / All Banks)</b>\n\n"
            "Select the amount you want to deposit into your wallet:\n"
            "<i>(Payment will generate an official dynamic KHQR)</i>"
        )
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=keyboards.deposit_amount_keyboard())
        except Exception:
            bot.send_message(chat_id, text, reply_markup=keyboards.deposit_amount_keyboard())
        bot.answer_callback_query(call.id)

    elif data.startswith("khqr_gen:"):
        amount = float(data.split("khqr_gen:")[1])
        bot.answer_callback_query(call.id, "Generating KHQR...")
        send_khqr_invoice(chat_id, user_id, amount)

    elif data == "khqr_custom":
        msg = bot.send_message(
            chat_id,
            "✏️ <b>Enter custom deposit amount in USD:</b>\n\n"
            "<i>Example: 2.50, 15, or 50 (Type /cancel to abort)</i>"
        )
        bot.register_next_step_handler(msg, process_custom_khqr_input)
        bot.answer_callback_query(call.id)

    elif data.startswith("khqr_check:"):
        dep_id = int(data.split("khqr_check:")[1])
        dep = database.get_deposit_request(dep_id)
        if not dep:
            bot.answer_callback_query(call.id, "Invoice not found!", show_alert=True)
            return

        if dep["status"] == "approved":
            user = database.get_user(user_id)
            bal = user["balance"] if user else 0.0
            bot.answer_callback_query(call.id, f"✅ Payment confirmed! Current balance: ${bal:.2f}", show_alert=True)
            return

        bot.answer_callback_query(call.id, "🔍 Verifying payment with NBC Bakong network...")
        res = khqr_service.check_bakong_transaction(dep["md5"], getattr(config, "BAKONG_API_TOKEN", ""))
        if res.get("paid"):
            success, new_bal, target_uid, amount = database.approve_deposit(dep_id)
            if success:
                try:
                    bot.edit_message_caption(
                        f"✅ <b>PAYMENT CONFIRMED!</b>\n\n"
                        f"Amount: <b>+${amount:.2f} {config.BAKONG_CURRENCY}</b>\n"
                        f"Invoice: <code>#DEP-{dep_id}</code>\n"
                        f"Status: <b>Verified via NBC Bakong</b>",
                        chat_id,
                        msg_id
                    )
                except Exception:
                    pass
                bot.send_message(
                    user_id,
                    f"🎉 <b>Payment Received!</b>\n\n"
                    f"Amount Credited: <b>+${amount:.2f} {config.BAKONG_CURRENCY}</b>\n"
                    f"💰 <b>New Wallet Balance:</b> <code>${new_bal:.2f}</code>\n\n"
                    f"You can now purchase accounts with your balance!",
                    reply_markup=keyboards.main_reply_keyboard(is_admin=admin_status)
                )
                for admin_id in config.ADMIN_IDS:
                    try:
                        bot.send_message(
                            admin_id,
                            f"🔔 <b>Manual KHQR Verification Succeeded!</b>\n\n"
                            f"👤 Customer: <code>{user_id}</code>\n"
                            f"💵 Amount: <b>${amount:.2f} {config.BAKONG_CURRENCY}</b>\n"
                            f"🔢 Invoice: <code>#DEP-{dep_id}</code>\n"
                            f"⚡ Verified: <b>NBC Bakong Ledger</b>"
                        )
                    except Exception:
                        pass
            else:
                bot.answer_callback_query(call.id, "Payment already processed!", show_alert=True)
        else:
            bot.answer_callback_query(
                call.id,
                "⏳ Payment not detected yet.\n\n"
                "If you completed the transfer, please wait 3-5 seconds for NBC Bakong network settlement, then tap again.",
                show_alert=True
            )

    # 2. Browse Products by Category
    elif data.startswith("cat:"):
        cat_id = data.split("cat:")[1]
        cat_name = "Category"
        for c in database.get_categories():
            if c["id"] == cat_id:
                cat_name = c["name"]
                break
        
        text = f"📁 <b>{cat_name}</b>\n\nSelect a product to view details and purchase:"
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=keyboards.products_keyboard(cat_id))
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    # 3. View Single Product
    elif data.startswith("prod:"):
        prod_id = int(data.split("prod:")[1])
        product = database.get_product(prod_id)
        if not product:
            bot.answer_callback_query(call.id, "Product not found!", show_alert=True)
            return
        
        stock_status = f"✅ <b>In Stock:</b> {product['stock_count']} available" if product['stock_count'] > 0 else "❌ <b>Out of Stock</b>"
        text = (
            f"📦 <b>{product['name']}</b>\n\n"
            f"📝 <b>Description:</b>\n{product['description']}\n\n"
            f"💵 <b>Price:</b> <code>{config.CURRENCY}{product['price']:.2f}</code>\n"
            f"📊 <b>Availability:</b> {stock_status}\n"
        )
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=keyboards.product_detail_keyboard(product))
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    # 4. Confirm Buy
    elif data.startswith("buy_confirm:"):
        prod_id = int(data.split("buy_confirm:")[1])
        product = database.get_product(prod_id)
        user = database.get_user(user_id)
        
        if not product or product["stock_count"] <= 0:
            bot.answer_callback_query(call.id, "Sorry, this product is out of stock!", show_alert=True)
            return

        text = (
            f"🛒 <b>Confirm Purchase</b>\n\n"
            f"Product: <b>{product['name']}</b>\n"
            f"Total Price: <b>{config.CURRENCY}{product['price']:.2f}</b>\n"
            f"Your Current Balance: <b>{config.CURRENCY}{user['balance']:.2f}</b>\n\n"
            f"Are you sure you want to purchase 1 account?"
        )
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=keyboards.confirm_buy_keyboard(prod_id))
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    # 5. Execute Buy
    elif data.startswith("buy_execute:"):
        prod_id = int(data.split("buy_execute:")[1])
        success, result_data, order_id = database.purchase_product(user_id, prod_id)

        if success:
            product = database.get_product(prod_id)
            user = database.get_user(user_id)
            order_text = (
                f"🎉 <b>Purchase Successful!</b>\n\n"
                f"📦 <b>Item:</b> {product['name']}\n"
                f"🔢 <b>Order ID:</b> <code>#{order_id}</code>\n"
                f"💵 <b>Amount Paid:</b> {config.CURRENCY}{product['price']:.2f}\n"
                f"💰 <b>Remaining Balance:</b> {config.CURRENCY}{user['balance']:.2f}\n\n"
                f"🔑 <b>Your Account Credentials:</b>\n"
                f"<code>{result_data}</code>\n\n"
                f"⚠️ <i>Please copy and save your account credentials immediately. You can also view this in 'My Orders'.</i>"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🛒 Buy Another", callback_data=f"cat:{product['category_id']}"))
            markup.add(types.InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:main"))
            try:
                bot.edit_message_text(order_text, chat_id, msg_id, reply_markup=markup)
            except Exception:
                bot.send_message(chat_id, order_text, reply_markup=markup)
            bot.answer_callback_query(call.id, "🎉 Purchase successful!")

            # Notify admins of the new sale
            for admin_id in config.ADMIN_IDS:
                try:
                    bot.send_message(
                        admin_id,
                        f"🔔 <b>New Sale Notification!</b>\n\n"
                        f"Customer: <code>{user_id}</code> (@{call.from_user.username or 'none'})\n"
                        f"Product: <b>{product['name']}</b>\n"
                        f"Revenue: <b>{config.CURRENCY}{product['price']:.2f}</b>\n"
                        f"Order ID: <code>#{order_id}</code>"
                    )
                except Exception:
                    pass

        elif result_data == "INSUFFICIENT_BALANCE":
            user = database.get_user(user_id)
            product = database.get_product(prod_id)
            text = (
                f"❌ <b>Insufficient Balance!</b>\n\n"
                f"Item Price: <b>{config.CURRENCY}{product['price']:.2f}</b>\n"
                f"Your Balance: <b>{config.CURRENCY}{user['balance']:.2f}</b>\n\n"
                f"Please top up your balance to complete this purchase."
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💳 Top Up / Deposit", callback_data="menu:deposit_info"))
            markup.add(types.InlineKeyboardButton("⬅️ Back to Product", callback_data=f"prod:{prod_id}"))
            try:
                bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)
            except Exception:
                pass
            bot.answer_callback_query(call.id, "Insufficient balance!", show_alert=True)

        elif result_data == "OUT_OF_STOCK":
            bot.answer_callback_query(call.id, "Sorry, this item just went out of stock!", show_alert=True)
            show_categories(chat_id, msg_id)
        else:
            bot.answer_callback_query(call.id, f"Error: {result_data}", show_alert=True)

    # 6. View Single Past Order
    elif data.startswith("view_order:"):
        order_id = int(data.split("view_order:")[1])
        order = database.get_order(order_id)
        if not order or order["user_id"] != user_id:
            bot.answer_callback_query(call.id, "Order not found!", show_alert=True)
            return

        text = (
            f"📦 <b>Order #{order['id']}</b>\n"
            f"Product: <b>{order['product_name']}</b>\n"
            f"Price: <b>{config.CURRENCY}{order['price']:.2f}</b>\n"
            f"Date: <i>{order['created_at']}</i>\n\n"
            f"🔑 <b>Delivered Account Data:</b>\n"
            f"<code>{order['account_data']}</code>\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Orders", callback_data="menu:orders"))
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    # 7. Admin Callbacks
    elif data == "admin:menu":
        if not admin_status: return
        show_admin_panel(chat_id, msg_id)
        bot.answer_callback_query(call.id)

    elif data == "admin:stats":
        if not admin_status: return
        stats = database.get_stats()
        text = (
            f"📊 <b>Detailed Store Statistics</b>\n\n"
            f"👥 Total Registered Users: <b>{stats['user_count']}</b>\n"
            f"📦 Total Stock Available: <b>{stats['stock_available']}</b> accounts\n"
            f"🛒 Total Accounts Sold: <b>{stats['sold_count']}</b>\n"
            f"💰 Total Revenue: <b>{config.CURRENCY}{stats['total_revenue']:.2f}</b>\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin:menu"))
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    elif data == "admin:select_product_stock":
        if not admin_status: return
        text = "➕ <b>Select Product to Add Stock:</b>\n\nChoose the product you want to upload accounts for:"
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=keyboards.admin_select_stock_product_keyboard())
        bot.answer_callback_query(call.id)

    elif data.startswith("admin_addstock:"):
        if not admin_status: return
        prod_id = int(data.split("admin_addstock:")[1])
        product = database.get_product(prod_id)
        text = (
            f"➕ <b>Adding Stock for: {product['name']}</b>\n\n"
            f"Please send the accounts as text (one per line) or as a .txt file.\n\n"
            f"<b>Example format:</b>\n"
            f"<code>email1@gmail.com:password123:recovery1@mail.com\n"
            f"email2@gmail.com:password456:recovery2@mail.com</code>\n\n"
            f"<i>Type /cancel to cancel.</i>"
        )
        msg = bot.send_message(chat_id, text)
        bot.register_next_step_handler(msg, process_stock_input, prod_id)
        bot.answer_callback_query(call.id)

    elif data == "admin:products":
        if not admin_status: return
        text = "📦 <b>Product Management:</b>\n\nTap a product to edit price or add stock:"
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=keyboards.admin_products_keyboard())
        bot.answer_callback_query(call.id)

    elif data.startswith("admin_prod:"):
        if not admin_status: return
        prod_id = int(data.split("admin_prod:")[1])
        product = database.get_product(prod_id)
        text = (
            f"📦 <b>{product['name']}</b>\n\n"
            f"Category: <code>{product['category_id']}</code>\n"
            f"Price: <b>{config.CURRENCY}{product['price']:.2f}</b>\n"
            f"Available Stock: <b>{product['stock_count']}</b>\n"
            f"Description:\n{product['description']}\n"
        )
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=keyboards.admin_product_detail_keyboard(prod_id))
        bot.answer_callback_query(call.id)

    elif data.startswith("admin_chprice:"):
        if not admin_status: return
        prod_id = int(data.split("admin_chprice:")[1])
        product = database.get_product(prod_id)
        msg = bot.send_message(
            chat_id, 
            f"✏️ <b>Enter new price for {product['name']}:</b>\n\nCurrent price: {config.CURRENCY}{product['price']:.2f}\n"
            f"<i>Example: 0.99 or 1.50 (Type /cancel to abort)</i>"
        )
        bot.register_next_step_handler(msg, process_price_input, prod_id)
        bot.answer_callback_query(call.id)

    elif data == "admin:users":
        if not admin_status: return
        users = database.get_all_users()[:15]
        user_list_text = f"👥 <b>Recent Users ({len(users)} shown):</b>\n\n"
        for u in users:
            uname = f"@{u['username']}" if u['username'] else "No username"
            user_list_text += f"• ID: <code>{u['user_id']}</code> | {uname} | Bal: <b>{config.CURRENCY}{u['balance']:.2f}</b>\n"
        
        user_list_text += "\n💡 <i>To add balance, use command:</i>\n<code>/addbalance &lt;user_id&gt; &lt;amount&gt;</code>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin:menu"))
        bot.edit_message_text(user_list_text, chat_id, msg_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    elif data == "admin:broadcast":
        if not admin_status: return
        msg = bot.send_message(
            chat_id,
            "📢 <b>Broadcast Announcement</b>\n\n"
            "Send the message you want to broadcast to all registered bot users:\n"
            "<i>(Type /cancel to abort)</i>"
        )
        bot.register_next_step_handler(msg, process_broadcast)
        bot.answer_callback_query(call.id)

    # Admin Deposit Approval / Rejection
    elif data.startswith("admin_appr_dep:"):
        if not admin_status: return
        dep_id = int(data.split("admin_appr_dep:")[1])
        success, new_bal, target_uid, amount = database.approve_deposit(dep_id)
        if success:
            bot.edit_message_caption(
                f"✅ <b>APPROVED!</b>\n\nCredited <b>+{config.CURRENCY}{amount:.2f}</b> to user <code>{target_uid}</code>.\nNew Balance: <b>{config.CURRENCY}{new_bal:.2f}</b>",
                chat_id,
                msg_id
            )
            try:
                bot.send_message(
                    target_uid,
                    f"🎉 <b>KHQR Deposit Approved!</b>\n\n"
                    f"Your payment of <b>+{config.CURRENCY}{amount:.2f}</b> has been verified and added to your wallet!\n"
                    f"💰 <b>New Balance:</b> <code>{config.CURRENCY}{new_bal:.2f}</code>\n\n"
                    f"You can now purchase accounts with your balance!"
                )
            except Exception as e:
                logger.warning(f"Could not notify user {target_uid}: {e}")
            bot.answer_callback_query(call.id, f"Approved +{config.CURRENCY}{amount:.2f}!")
        else:
            bot.answer_callback_query(call.id, "Already processed or error!", show_alert=True)

    elif data.startswith("admin_rej_dep:"):
        if not admin_status: return
        dep_id = int(data.split("admin_rej_dep:")[1])
        success, target_uid, amount = database.reject_deposit(dep_id)
        if success:
            bot.edit_message_caption(
                f"❌ <b>REJECTED</b> deposit invoice #{dep_id} ({config.CURRENCY}{amount:.2f}).",
                chat_id,
                msg_id
            )
            try:
                bot.send_message(
                    target_uid,
                    f"❌ <b>Deposit Update:</b>\n\n"
                    f"Your deposit request <code>#DEP-{dep_id}</code> ({config.CURRENCY}{amount:.2f}) was rejected by Admin.\n"
                    f"Please contact support if you need assistance."
                )
            except Exception:
                pass
            bot.answer_callback_query(call.id, "Deposit rejected.")
        else:
            bot.answer_callback_query(call.id, "Already processed or error!", show_alert=True)

    elif data == "noop":
        bot.answer_callback_query(call.id, "This product is currently out of stock.")

# Admin Next Step Handlers
def process_stock_input(message: types.Message, prod_id: int):
    if message.text and message.text.strip() == "/cancel":
        bot.send_message(message.chat.id, "❌ Cancelled adding stock.")
        return

    lines = []
    if message.document:
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            content = downloaded.decode("utf-8", errors="ignore")
            lines = [l.strip() for l in content.splitlines() if l.strip()]
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Failed reading file: {e}")
            return
    elif message.text:
        lines = [l.strip() for l in message.text.splitlines() if l.strip()]

    if not lines:
        bot.send_message(message.chat.id, "⚠️ No valid lines received. Operation cancelled.")
        return

    added = database.add_stock(prod_id, lines)
    product = database.get_product(prod_id)
    bot.send_message(
        message.chat.id,
        f"✅ <b>Successfully added {added} accounts!</b>\n\n"
        f"Product: <b>{product['name']}</b>\n"
        f"Total Stock Available Now: <b>{product['stock_count']}</b>",
        reply_markup=keyboards.admin_menu_keyboard()
    )

def process_price_input(message: types.Message, prod_id: int):
    if message.text and message.text.strip() == "/cancel":
        bot.send_message(message.chat.id, "❌ Cancelled price change.")
        return
    try:
        new_price = float(message.text.strip())
        if new_price < 0:
            raise ValueError
        database.update_product_price(prod_id, new_price)
        product = database.get_product(prod_id)
        bot.send_message(
            message.chat.id,
            f"✅ <b>Price updated!</b>\n\n"
            f"Product: <b>{product['name']}</b>\n"
            f"New Price: <b>{config.CURRENCY}{new_price:.2f}</b>",
            reply_markup=keyboards.admin_menu_keyboard()
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid price. Operation cancelled.")

def process_broadcast(message: types.Message):
    if message.text and message.text.strip() == "/cancel":
        bot.send_message(message.chat.id, "❌ Cancelled broadcast.")
        return
    
    text = message.text
    if not text:
        bot.send_message(message.chat.id, "⚠️ Only text broadcast supported. Cancelled.")
        return

    users = database.get_all_users()
    sent_count = 0
    fail_count = 0

    status_msg = bot.send_message(message.chat.id, f"🚀 Broadcasting to {len(users)} users...")

    for u in users:
        try:
            bot.send_message(u["user_id"], f"📢 <b>Announcement:</b>\n\n{text}")
            sent_count += 1
        except Exception:
            fail_count += 1

    bot.edit_message_text(
        f"✅ <b>Broadcast Completed!</b>\n\n"
        f"Delivered: <b>{sent_count}</b>\n"
        f"Failed/Blocked: <b>{fail_count}</b>",
        message.chat.id,
        status_msg.message_id
    )

def process_custom_khqr_input(message: types.Message):
    if message.text and message.text.strip() == "/cancel":
        bot.send_message(message.chat.id, "❌ Cancelled deposit.")
        return
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
        send_khqr_invoice(message.chat.id, message.from_user.id, amount)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount. Must be a positive number (e.g. 5.00).")

def process_deposit_receipt(message: types.Message, dep_id: int):
    if message.text and message.text.strip() == "/cancel":
        bot.send_message(message.chat.id, "❌ Cancelled receipt submission.")
        return
    
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id

    if not file_id:
        msg = bot.send_message(message.chat.id, "⚠️ Please send a screenshot/photo of your payment receipt. (Or send /cancel)")
        bot.register_next_step_handler(msg, process_deposit_receipt, dep_id)
        return

    dep = database.get_deposit_request(dep_id)
    if not dep:
        bot.send_message(message.chat.id, "❌ Deposit invoice not found.")
        return

    database.update_deposit_receipt(dep_id, file_id)

    bot.send_message(
        message.chat.id,
        f"✅ <b>Receipt Received for Invoice #{dep_id}!</b>\n\n"
        f"Amount: <b>${dep['amount']:.2f} {dep['currency']}</b>\n"
        f"Your payment has been submitted to Admin for instant verification.\n"
        f"Your balance will be credited within 1-5 minutes.",
        reply_markup=keyboards.main_reply_keyboard(is_admin=is_admin(message.from_user.id))
    )

    # Forward receipt to all admins for 1-click approval
    username = f"@{message.from_user.username}" if message.from_user.username else f"{message.from_user.first_name}"
    for admin_id in config.ADMIN_IDS:
        try:
            admin_text = (
                f"🔔 <b>New KHQR Deposit Submitted!</b>\n\n"
                f"👤 <b>Customer:</b> {username} (ID: <code>{message.from_user.id}</code>)\n"
                f"💵 <b>Amount:</b> <b>${dep['amount']:.2f} {dep['currency']}</b>\n"
                f"🔢 <b>Invoice:</b> <code>#DEP-{dep_id}</code>\n"
                f"📅 <b>Date:</b> {dep['created_at']}\n\n"
                f"Review receipt below and tap Approve or Reject:"
            )
            bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=admin_text,
                reply_markup=keyboards.admin_deposit_approval_keyboard(dep_id)
            )
        except Exception as e:
            logger.error(f"Failed sending receipt to admin {admin_id}: {e}")

if __name__ == "__main__":
    database.init_db()
    print("==================================================")
    print("🤖 ICbuy Telegram Shop Bot is starting...")
    print("==================================================")
    
    # Verify token before starting polling
    try:
        bot_info = bot.get_me()
        print(f"✅ Connected to Telegram successfully as: @{bot_info.username} ({bot_info.first_name})")
        print(f"📡 Bot is now running and listening for messages!")
        print("💡 Press Ctrl+C in this terminal to stop.")
        print("==================================================")
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 401:
            print("\n❌ [ERROR 401: UNAUTHORIZED]")
            print("Telegram rejected your BOT_TOKEN!")
            print("This means the token in your .env file is invalid or was revoked.\n")
            print("👉 How to fix:")
            print("1. Open Telegram and message @BotFather")
            print("2. Send: /mybots")
            print("3. Click: @icbuy_bot -> API Token (or 'Revoke current token')")
            print("4. Copy the new token and paste it into the .env file:")
            print("   BOT_TOKEN=your_new_token_here\n")
            print("Then run python bot.py again.")
            print("==================================================")
        elif e.error_code == 409:
            print("\n❌ [ERROR 409: CONFLICT - MULTIPLE INSTANCES]")
            print("Another window or process is already running this bot!")
            print("Telegram only allows ONE bot instance running at a time.\n")
            print("👉 How to fix:")
            print("1. Close any other terminal / command prompt windows running bot.py")
            print("2. Run python bot.py again.")
            print("==================================================")
        else:
            logger.error(f"Telegram API Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
