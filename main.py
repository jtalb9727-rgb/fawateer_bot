import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# نقرأ التوكن من Variables
TOKEN = os.environ.get("BOT_TOKEN")

# دالة /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت شغال! اهلا بك في بوت الفواتير")

def main():
    # نتأكد ان التوكن موجود
    if not TOKEN:
        print("BOT_TOKEN مش موجود!")
        return
    
    # ننشئ التطبيق
    app = Application.builder().token(TOKEN).build()
    
    # نضيف امر /start
    app.add_handler(CommandHandler("start", start))
    
    # نشغل البوت
    print("البوت اشتغل...")
    app.run_polling()

if __name__ == "__main__":
    main()
