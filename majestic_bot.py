if __name__ == '__main__':
    # Flask в фоне
    port = int(os.environ.get('PORT', 5000))
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True)
    flask_thread.start()
    
    # Бот в основном потоке
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_key))
    application.add_handler(CommandHandler("revoke", revoke_key))
    application.add_handler(CommandHandler("keys", list_keys))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("hwid", show_hwid))
    application.add_handler(CommandHandler("unbind", unbind_hwid))
    
    print("Bot started")
    application.run_polling()
