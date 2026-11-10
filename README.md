# 🤖 ICbuy Telegram Account Store Bot

A full-featured Telegram Store Bot for selling **Gmail**, **Facebook**, and other digital accounts with automated instant delivery, wallet/balance system, and built-in Admin management panel.

---

## 🌟 Features

- 🛒 **Instant Automated Delivery**: Accounts are delivered to customers directly inside Telegram chat immediately after payment.
- 📧 **Gmail & Facebook Catalog**: Organized categories for Aged Gmail, Fresh Gmail, 2FA Gmail, Facebook Profiles, etc.
- 💰 **Wallet & Balance System**:
  - Users have personal wallet balances.
  - Users can view balance, request deposit details, and submit payment proof.
  - Admin can credit balances using `/addbalance <user_id> <amount>`.
- 📊 **Admin Dashboard (`/admin`)**:
  - **Add Stock**: Paste accounts as text or upload `.txt` file directly in Telegram.
  - **Manage Products & Prices**: Edit prices on-the-fly.
  - **Live Store Stats**: View total users, accounts sold, available stock, and revenue.
  - **Broadcast**: Send announcements to all registered users with 1 click.
- 📜 **Order History**: Users can review their past purchases and view credentials anytime.
- ⚡ **Zero Setup Database**: Uses SQLite (`shop.db`) with atomic transactions (prevents double-selling accounts).

---

## 🚀 Quick Setup Guide

### 1. Configure `.env`
Open the [`.env`](file:///d:/BOT%20account/.env) file:

```env
# Your Bot Token from @BotFather
BOT_TOKEN=your_bot_token_here

# Your Telegram User ID (get it by sending /id to the bot)
ADMIN_IDS=123456789

# Currency symbol (e.g. $, USD, ฿, ₫)
CURRENCY=$

# Your support / admin telegram username
SUPPORT_CONTACT=@your_admin_username
```

> 💡 **How to find your Telegram User ID:**
> 1. Start your bot and send `/id`.
> 2. The bot will reply with your numeric ID (e.g. `123456789`).
> 3. Paste it into `ADMIN_IDS` in `.env` and restart the bot.

---

### 2. Run the Bot

Open PowerShell / Terminal in `d:\BOT account` and run:

```powershell
python bot.py
```

---

## 📦 How to Add Stock (Gmail / Facebook Accounts)

1. Open your bot on Telegram and type `/admin` (or click `⚙️ Admin Panel`).
2. Tap **➕ Add Stock**.
3. Choose the product (e.g., `Gmail Aged` or `Facebook Profile`).
4. Paste your account lines directly into the chat:
   ```text
   user1@gmail.com:password123:recovery1@mail.com
   user2@gmail.com:password456:recovery2@mail.com
   ```
   *Or upload a `.txt` file containing the accounts.*
5. The bot will automatically add them to available stock!

---

## 💵 How to Add Balance to a Customer

When a customer pays you:
1. Ask the customer for their Telegram ID (they can get it by typing `/id` or looking at `/start`).
2. Type in chat:
   ```text
   /addbalance <user_id> <amount>
   ```
   *Example:*
   ```text
   /addbalance 123456789 10.00
   ```
3. The customer receives an instant notification: `🎉 Balance Credited! +$10.00`.

---

## 📁 File Structure

- [`bot.py`](file:///d:/BOT%20account/bot.py) - Main bot execution & message handlers.
- [`database.py`](file:///d:/BOT%20account/database.py) - SQLite database logic, user balances, atomic stock checkout.
- [`keyboards.py`](file:///d:/BOT%20account/keyboards.py) - Telegram inline and reply keyboards.
- [`config.py`](file:///d:/BOT%20account/config.py) - Settings & environment variables.
- [`.env`](file:///d:/BOT%20account/.env) - Secret bot token and admin IDs.
- [`sample_stock.txt`](file:///d:/BOT%20account/sample_stock.txt) - Sample format for account inventory.
