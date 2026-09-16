import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text("هلا والله يا ادمن جمال 🚀 البوت شغال 100%")
    else:
        await update.message.reply_text("اهلاً، هذا بوت خاص بجمال")
def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    print("Bot is running...")
    application.run_polling()
if __name__ == '__main__':
    main()
