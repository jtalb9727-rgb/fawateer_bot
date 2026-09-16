import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler

# تفعيل اللوق عشان نشوف الاخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# نقرأ التوكن من Variables
TOKEN = os.getenv("BOT_TOKEN")

# دالة /start
async def start(update, context):
    await update.message.reply_text('اهلاً! البوت اشتغل بنجاح 🎉')

if __name__ == '__main__':
    print("PTB Version:", "20.7")
    print("البوت اشتغل...")
    
    # نبني البوت بالطريقة الجديدة حق v20
    app = ApplicationBuilder().token(TOKEN).build()
    
    # نضيف امر /start
    app.add_handler(CommandHandler("start", start))
    
    # نشغل البوت
    app.run_polling()
