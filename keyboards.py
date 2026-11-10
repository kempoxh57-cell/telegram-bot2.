from telebot import types
import config
import database

def main_reply_keyboard(is_admin: bool = False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_buy = types.KeyboardButton("🛒 Buy Accounts")
    btn_balance = types.KeyboardButton("💰 My Balance / Deposit")
    btn_orders = types.KeyboardButton("📜 My Orders")
    btn_support = types.KeyboardButton("ℹ️ Support")
    markup.add(btn_buy, btn_balance)
    markup.add(btn_orders, btn_support)
    if is_admin:
        btn_admin = types.KeyboardButton("⚙️ Admin Panel")
        markup.add(btn_admin)
    return markup

def main_inline_menu(is_admin: bool = False):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_gmail = types.InlineKeyboardButton("📧 Buy Gmail", callback_data="cat:gmail")
    btn_fb = types.InlineKeyboardButton("📘 Buy Facebook", callback_data="cat:facebook")
    btn_other = types.InlineKeyboardButton("🌐 Other Accounts", callback_data="cat:other")
    btn_balance = types.InlineKeyboardButton("💰 Balance & Deposit", callback_data="menu:balance")
    btn_orders = types.InlineKeyboardButton("📜 My Orders", callback_data="menu:orders")
    btn_support = types.InlineKeyboardButton("ℹ️ Support", callback_data="menu:support")
    
    markup.add(btn_gmail, btn_fb)
    markup.add(btn_other, btn_balance)
    markup.add(btn_orders, btn_support)
    if is_admin:
        btn_admin = types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin:menu")
        markup.add(btn_admin)
    return markup

def categories_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    categories = database.get_categories()
    for cat in categories:
        markup.add(types.InlineKeyboardButton(cat["name"], callback_data=f"cat:{cat['id']}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu:main"))
    return markup

def products_keyboard(category_id: str):
    markup = types.InlineKeyboardMarkup(row_width=1)
    products = database.get_products_by_category(category_id)
    for p in products:
        stock = p["stock_count"]
        stock_text = f"({stock} in stock)" if stock > 0 else "(Out of stock)"
        btn_text = f"{p['name']} - {config.CURRENCY}{p['price']:.2f} {stock_text}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"prod:{p['id']}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back to Categories", callback_data="menu:categories"))
    return markup

def product_detail_keyboard(product: dict):
    markup = types.InlineKeyboardMarkup(row_width=1)
    stock = product["stock_count"]
    if stock > 0:
        markup.add(types.InlineKeyboardButton(
            f"🛒 Buy Now ({config.CURRENCY}{product['price']:.2f})", 
            callback_data=f"buy_confirm:{product['id']}"
        ))
    else:
        markup.add(types.InlineKeyboardButton("❌ Out of Stock", callback_data="noop"))
    
    markup.add(types.InlineKeyboardButton("⬅️ Back to Products", callback_data=f"cat:{product['category_id']}"))
    return markup

def confirm_buy_keyboard(product_id: int):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_yes = types.InlineKeyboardButton("✅ Confirm & Pay", callback_data=f"buy_execute:{product_id}")
    btn_no = types.InlineKeyboardButton("❌ Cancel", callback_data=f"prod:{product_id}")
    markup.add(btn_yes, btn_no)
    return markup

def balance_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🇰🇭 Deposit via KHQR (Bakong / ABA / All Banks)", callback_data="deposit:select_amount"))
    markup.add(types.InlineKeyboardButton("💳 Other Payment Info", callback_data="menu:deposit_info"))
    markup.add(types.InlineKeyboardButton("💬 Contact Support", url=f"https://t.me/{config.SUPPORT_CONTACT.lstrip('@')}"))
    markup.add(types.InlineKeyboardButton("🔄 Refresh Balance", callback_data="menu:balance"))
    markup.add(types.InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:main"))
    return markup

def deposit_amount_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("$1.00", callback_data="khqr_gen:1.0")
    b2 = types.InlineKeyboardButton("$2.00", callback_data="khqr_gen:2.0")
    b5 = types.InlineKeyboardButton("$5.00", callback_data="khqr_gen:5.0")
    b10 = types.InlineKeyboardButton("$10.00", callback_data="khqr_gen:10.0")
    b20 = types.InlineKeyboardButton("$20.00", callback_data="khqr_gen:20.0")
    b50 = types.InlineKeyboardButton("$50.00", callback_data="khqr_gen:50.0")
    b_custom = types.InlineKeyboardButton("✏️ Custom Amount", callback_data="khqr_custom")
    b_back = types.InlineKeyboardButton("⬅️ Back to Wallet", callback_data="menu:balance")
    
    markup.add(b1, b2)
    markup.add(b5, b10)
    markup.add(b20, b50)
    markup.add(b_custom)
    markup.add(b_back)
    return markup

def khqr_payment_keyboard(deposit_id: int, deeplink: str = None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if deeplink:
        markup.add(types.InlineKeyboardButton("📱 1-Tap Pay with Bakong App", url=deeplink))
    markup.add(types.InlineKeyboardButton("🔄 Check Payment Status Now", callback_data=f"khqr_check:{deposit_id}"))
    markup.add(types.InlineKeyboardButton("❌ Cancel Payment", callback_data="menu:balance"))
    return markup

def admin_deposit_approval_keyboard(deposit_id: int):
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_app = types.InlineKeyboardButton("✅ Approve", callback_data=f"admin_appr_dep:{deposit_id}")
    b_rej = types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_rej_dep:{deposit_id}")
    markup.add(b_app, b_rej)
    return markup

def orders_keyboard(orders: list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for o in orders:
        btn_text = f"Order #{o['id']} - {o['product_name']} ({config.CURRENCY}{o['price']:.2f})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"view_order:{o['id']}"))
    markup.add(types.InlineKeyboardButton("⬅️ Main Menu", callback_data="menu:main"))
    return markup

# Admin Keyboards
def admin_menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add_stock = types.InlineKeyboardButton("➕ Add Stock", callback_data="admin:select_product_stock")
    btn_stats = types.InlineKeyboardButton("📊 Store Stats", callback_data="admin:stats")
    btn_products = types.InlineKeyboardButton("📦 Products & Prices", callback_data="admin:products")
    btn_users = types.InlineKeyboardButton("👥 Users List", callback_data="admin:users")
    btn_broadcast = types.InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast")
    btn_close = types.InlineKeyboardButton("⬅️ Exit Admin", callback_data="menu:main")
    
    markup.add(btn_add_stock, btn_stats)
    markup.add(btn_products, btn_users)
    markup.add(btn_broadcast)
    markup.add(btn_close)
    return markup

def admin_products_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    products = database.get_all_products()
    for p in products:
        btn_text = f"#{p['id']} {p['name']} ({config.CURRENCY}{p['price']:.2f} | Stock: {p['stock_count']})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_prod:{p['id']}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin:menu"))
    return markup

def admin_product_detail_keyboard(product_id: int):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_stock = types.InlineKeyboardButton("➕ Add Stock", callback_data=f"admin_addstock:{product_id}")
    btn_price = types.InlineKeyboardButton("✏️ Change Price", callback_data=f"admin_chprice:{product_id}")
    btn_back = types.InlineKeyboardButton("⬅️ Back", callback_data="admin:products")
    markup.add(btn_stock, btn_price)
    markup.add(btn_back)
    return markup

def admin_select_stock_product_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    products = database.get_all_products()
    for p in products:
        btn_text = f"#{p['id']} {p['name']} (Stock: {p['stock_count']})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_addstock:{p['id']}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin:menu"))
    return markup
