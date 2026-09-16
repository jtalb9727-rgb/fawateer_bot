import os
from telegram.ext import Application, CommandHandler

# ناخذ التوكن من Railway Variables
TOKEN = os.environ.get("BOT_TOKEN")

# امر /start = للتأكد ان البوت وصل
async def start(update, context):
    await update.message.reply_text("✅ تم الاتصال بنجاح\nالبوت شغال على Railway 100%")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("البوت اشتغل...")
    app.run_polling()

if __name__ == '__main__':
    main()
