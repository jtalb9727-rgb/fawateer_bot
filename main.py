import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text('اهلاً! البوت اشتغل بنجاح 🎉')

if __name__ == '__main__':
    print("PTB Version: 20.7")
    print("البوت اشتغل...")
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
