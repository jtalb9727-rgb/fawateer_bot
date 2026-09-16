import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

async def start(update, context):
    await update.message.reply_text(f"اهلا {update.effective_user.first_name} انا شغال ✅")

async def echo(update, context):
    await context.bot.send_message(
        chat_id=ADMIN_ID, 
        text=f"رسالة من {update.effective_user.first_name}: {update.message.text}"
    )
    await update.message.reply_text("تم ارسال رسالتك للادمن")

def main():
    if not TOKEN:
        raise ValueError("ضيف TOKEN في Variables")
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
