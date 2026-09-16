import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت شغال! اهلا بك في بوت الفواتير")

def main():
    if not TOKEN:
        print("BOT_TOKEN مش موجود!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("البوت اشتغل...")
    app.run_polling()

if __name__ == "__main__":
    main()
