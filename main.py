import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import telegram
print(f"PTB Version: {telegram.__version__}") # هذا السطر جديد

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت شغال! اهلا بك")

def main():
    if not TOKEN:
        print("BOT_TOKEN مش موجود!")
        return
    print("البوت اشتغل...") # هذا السطر جديد
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
