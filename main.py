import os
import sqlite3
import json
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ======== الاعدادات الاساسية ========
TOKEN = os.environ.get('TOKEN') # توكن بوت التحكم حقك
ADMIN_ID = int(os.environ.get('ADMIN_ID')) # الايدي حقك انت
YOUR_NUMBER = 772765410 # رقمك عشان تنبيه الاشتراكات
SUBSCRIPTION_PRICE = 20000 # قيمة الاشتراك الشهري

logging.basicConfig(level=logging.INFO)

# ======== قاعدة البيانات ========
def init_db():
    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS restaurants
                 (id INTEGER PRIMARY KEY,
                  name TEXT UNIQUE,
                  owner_id TEXT,
                  start_date TEXT,
                  end_date TEXT,
                  status TEXT DEFAULT 'active',
                  token TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoices_log
                 (id INTEGER PRIMARY KEY,
                  restaurant_name TEXT,
                  count_today INTEGER DEFAULT 0,
                  total_today REAL DEFAULT 0,
                  last_invoice_time TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ======== دالة التحقق من الادمن ========
def is_admin(user_id):
    return user_id == ADMIN_ID

# ======== /start ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("بوت تحكم الفواتير شغال ✅\n\nالاوامر:\n/add\n/stop\n/start\n/devices\n/alert\n/log")

# ======== /add رقم اسم المطعم المدة ========
async def add_restaurant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        owner_id = context.args[0] # 967771234567
        name = context.args[1] # مطعم_البيك
        days = int(context.args[2]) # 30

        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(days=days)
        token = os.urandom(16).hex() # توكن خاص بالمطعم

        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("INSERT INTO restaurants (name, owner_id, start_date, end_date, token) VALUES (?,?,?,?,?)",
                  (name, owner_id, start_date.isoformat(), end_date.isoformat(), token))
        conn.commit()
        conn.close()

        # توليد config.json
        config = {
            "restaurant_name": name,
            "owner_telegram_id": owner_id,
            "device_name": "جهاز1",
            "api_endpoint": "https://your-api-url.com/check", # بتغيره بعدين
            "restaurant_token": token
        }

        config_str = json.dumps(config, ensure_ascii=False, indent=2)

        # ارسال الملف لك
        await update.message.reply_document(
            document=bytes(config_str, 'utf-8'),
            filename=f"config_{name}.json",
            caption=f"✅ تم اضافة {name}\nالمالك: {owner_id}\nينتهي: {end_date.date()}"
        )

        # تنبيه لك انت على رقمك 772765410
        alert_text = f"🔔 اشتراك جديد!\nالمطعم: {name}\nالمالك: {owner_id}\nالمبلغ: {SUBSCRIPTION_PRICE:,} ريال\nالمدة: {days} يوم"
        await context.bot.send_message(chat_id=ADMIN_ID, text=alert_text)

    except Exception as e:
        await update.message.reply_text(f"خطأ: تأكد من الصيغة\n/add 967771234567 مطعم_البيك 30\n\n{e}")

# ======== /stop اسم_المطعم ========
async def stop_restaurant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        name = context.args[0]
        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("UPDATE restaurants SET status='stopped' WHERE name=?", (name,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"⛔ تم ايقاف الارسال عن {name}\nالكاشير بيحفظ بس ما يرسل")
    except:
        await update.message.reply_text("استخدم: /stop اسم_المطعم")

# ======== /start اسم_المطعم - تشغيل ========
async def start_restaurant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        name = context.args[0]
        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("UPDATE restaurants SET status='active' WHERE name=?", (name,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ تم تشغيل الارسال لـ {name}")
    except:
        await update.message.reply_text("استخدم: /start اسم_المطعم")

# ======== /devices اسم_المطعم العدد ========
async def devices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        name = context.args[0]
        count = int(context.args[1])

        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("SELECT owner_id, token FROM restaurants WHERE name=?", (name,))
        row = c.fetchone()
        conn.close()

        if not row:
            await update.message.reply_text("المطعم غير موجود")
            return

        owner_id, token = row

        for i in range(1, count + 1):
            config = {
                "restaurant_name": name,
                "owner_telegram_id": owner_id,
                "device_name": f"جهاز{i}",
                "api_endpoint": "https://your-api-url.com/check",
                "restaurant_token": token
            }
            config_str = json.dumps(config, ensure_ascii=False, indent=2)
            await update.message.reply_document(
                document=bytes(config_str, 'utf-8'),
                filename=f"config_{name}_جهاز{i}.json"
            )
        await update.message.reply_text(f"✅ تم توليد {count} ملفات لـ {name}")
    except:
        await update.message.reply_text("استخدم: /devices اسم_المطعم 3")

# ======== /alert ========
async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    today = datetime.datetime.now()
    three_days = today + datetime.timedelta(days=3)

    c.execute("SELECT name, end_date FROM restaurants WHERE end_date <=? AND status='active'", (three_days.isoformat(),))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("✅ كل الاشتراكات تمام")
        return

    text = "⚠️ مطاعم قرب ينتهي اشتراكها:\n\n"
    keyboard = []
    for name, end_date in rows:
        end = datetime.datetime.fromisoformat(end_date)
        days_left = (end - today).days
        text += f"• {name} - باقي {days_left} يوم - ينتهي {end.date()}\n"
        keyboard.append([InlineKeyboardButton(f"⛔ ايقاف {name}", callback_data=f"stop_{name}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

# ======== /log اسم_المطعم ========
async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        name = context.args[0]
        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("SELECT status FROM restaurants WHERE name=?", (name,))
        status_row = c.fetchone()

        c.execute("SELECT count_today, total_today, last_invoice_time FROM invoices_log WHERE restaurant_name=?", (name,))
        log_row = c.fetchone()
        conn.close()

        if not status_row:
            await update.message.reply_text("المطعم غير موجود")
            return

        status = "شغال ✅" if status_row[0] == 'active' else "واقف ⛔"
        count = log_row[0] if log_row else 0
        total = log_row[1] if log_row else 0
        last = log_row[2] if log_row and log_row[2] else "لا يوجد"

        text = f"📊 {name}\nفواتير اليوم: {count}\nالمجموع: {total:,.0f} ريال\nاخر فاتورة: {last}\nالحالة: {status}"
        await update.message.reply_text(text)
    except:
        await update.message.reply_text("استخدم: /log اسم_المطعم")

# ======== ازرار الايقاف ========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    await query.answer()

    if query.data.startswith("stop_"):
        name = query.data.replace("stop_", "")
        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("UPDATE restaurants SET status='stopped' WHERE name=?", (name,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"⛔ تم ايقاف {name}")

# ======== تشغيل البوت ========
def main():
    if not TOKEN or not ADMIN_ID:
        print("ERROR: TOKEN or ADMIN_ID not set")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_restaurant))
    app.add_handler(CommandHandler("stop", stop_restaurant))
    app.add_handler(CommandHandler("start", start_restaurant))
    app.add_handler(CommandHandler("devices", devices))
    app.add_handler(CommandHandler("alert", alert))
    app.add_handler(CommandHandler("log", log))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
