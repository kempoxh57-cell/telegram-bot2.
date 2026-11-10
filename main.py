import bot

if __name__ == "__main__":
    bot.database.init_db()
    print("==================================================")
    print("🤖 ICbuy Telegram Shop Bot is starting...")
    print("==================================================")
    try:
        bot_info = bot.bot.get_me()
        print(f"✅ Connected to Telegram successfully as: @{bot_info.username} ({bot_info.first_name})")
        print(f"📡 Bot is now running and listening for messages!")
        print("💡 Press Ctrl+C in this terminal to stop.")
        print("==================================================")
        bot.bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        print(f"Error: {e}")
