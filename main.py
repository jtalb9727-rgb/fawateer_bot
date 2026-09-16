import os
import sqlite3
import json
import datetime
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# ======== الاعدادات الاساسية ========
TOKEN = os.environ.get('TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID'))
YOUR_NUMBER = 772765410 # رقمك للتنبيهات
SUBSCRIPTION_PRICE = 20000

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

def is_admin(user_id):
    return user_id == ADMIN_ID

# ======== 1. /start ========
def start_command(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    update.message.reply_text(
        "بوت تحكم الفواتير شغال ✅\n\n"
        "الاوامر:\n"
        "/add 967771234567 اسم_المطعم 30\n"
        "/stop اسم_المطعم\n"
        "/start اسم_المطعم\n"
        "/devices اسم_المطعم 3\n"
        "/alert\n"
        "/log اسم_المطعم"
    )

# ======== 2. /add - مصلحة 100% ========
def add_restaurant(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    try:
        if len(context.args) < 3:
            update.message.reply_text(
                "خطأ: الصيغة غلط\n\n"
                "الصح:\n/add 967771234567 اسم_المطعم 30\n\n"
                "مثال:\n/add 967777586577 رشيد_العبيدي 30"
            )
            return

        owner_id = context.args[0]
        days = int(context.args[-1]) # اخر عنصر هو الايام
        name = " ".join(context.args[1:-1]) # كل اللي بالنص هو الاسم

        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(days=days)
        token = os.urandom(16).hex()

        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("INSERT INTO restaurants (name, owner_id, start_date, end_date, token) VALUES (?,?,?,?,?)",
                  (name, owner_id, start_date.isoformat(), end_date.isoformat(), token))
        conn.commit()
        conn.close()

        config = {
            "restaurant_name": name,
            "owner_telegram_id": owner_id,
            "device_name": "جهاز1",
            "api_endpoint": "https://your-api-url.com/check",
            "restaurant_token": token
        }
        config_str = json.dumps(config, ensure_ascii=False, indent=2)

        # 1. يرسل لك ملف config.json
        update.message.reply_document(
            document=bytes(config_str, 'utf-8'),
            filename=f"config_{name.replace(' ', '_')}.json",
            caption=f"✅ تم اضافة {name}\nالمالك: {owner_id}\nينتهي: {end_date.date()}"
        )

        # 2. يرسل لك تنبيه على رقمك 772765410
        alert_text = f"🔔 اشتراك جديد!\nالمطعم: {name}\nالمالك: {owner_id}\nالمبلغ: {SUBSCRIPTION_PRICE:,} ريال\nالمدة: {days} يوم"
        context.bot.send_message(chat_id=ADMIN_ID, text=alert_text)

    except ValueError:
        update.message.reply_text("خطأ: عدد الايام لازم رقم\nمثال: 30")
    except sqlite3.IntegrityError:
        update.message.reply_text("خطأ: اسم المطعم موجود من قبل")
    except Exception as e:
        update.message.reply_text(f"خطأ: {e}")

# ======== 3. /stop ========
def stop_restaurant(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    try:
        name = " ".join(context.args)
        if not name:
            update.message.reply_text("استخدم: /stop اسم_المطعم")
            return
            
        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("UPDATE restaurants SET status='stopped' WHERE name=?", (name,))
        if c.rowcount == 0:
            update.message.reply_text("المطعم غير موجود")
        else:
            conn.commit()
            update.message.reply_text(f"⛔ تم ايقاف الارسال عن {name}")
        conn.close()
    except:
        update.message.reply_text("خطأ في الايقاف")

# ======== 4. /start - تشغيل مطعم ========
def start_restaurant(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    try:
        name = " ".join(context.args)
        if not name:
            update.message.reply_text("استخدم: /start اسم_المطعم")
            return
            
        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("UPDATE restaurants SET status='active' WHERE name=?", (name,))
        if c.rowcount == 0:
            update.message.reply_text("المطعم غير موجود")
        else:
            conn.commit()
            update.message.reply_text(f"✅ تم تشغيل الارسال لـ {name}")
        conn.close()
    except:
        update.message.reply_text("خطأ في التشغيل")

# ======== 5. /devices ========
def devices(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    try:
        if len(context.args) < 2:
            update.message.reply_text("استخدم: /devices اسم_المطعم 3")
            return
            
        count = int(context.args[-1])
        name = " ".join(context.args[:-1])
        
        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("SELECT owner_id, token FROM restaurants WHERE name=?", (name,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            update.message.reply_text("المطعم غير موجود")
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
            update.message.reply_document(
                document=bytes(config_str, 'utf-8'),
                filename=f"config_{name.replace(' ', '_')}_جهاز{i}.json"
            )
        update.message.reply_text(f"✅ تم توليد {count} ملفات لـ {name}")
    except ValueError:
        update.message.reply_text("عدد الاجهزة لازم رقم\nمثال: /devices رشيد_العبيدي 3")
    except:
        update.message.reply_text("خطأ في توليد الاجهزة")

# ======== 6. /alert ========
def alert(update: Update, context: CallbackContext):
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
        update.message.reply_text("✅ كل الاشتراكات تمام")
        return
        
    text = "⚠️ مطاعم قرب ينتهي اشتراكها:\n\n"
    for name, end_date in rows:
        end = datetime.datetime.fromisoformat(end_date)
        days_left = (end - today).days
        text += f"• {name} - باقي {days_left} يوم - ينتهي {end.date()}\n/stop {name}\n\n"
    
    update.message.reply_text(text)

# ======== 7. /log ========
def log(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    try:
        name = " ".join(context.args)
        if not name:
            update.message.reply_text("استخدم: /log اسم_المطعم")
            return
            
        conn = sqlite3.connect('restaurants.db')
        c = conn.cursor()
        c.execute("SELECT status FROM restaurants WHERE name=?", (name,))
        status_row = c.fetchone()
        c.execute("SELECT count_today, total_today, last_invoice_time FROM invoices_log WHERE restaurant_name=?", (name,))
        log_row = c.fetchone()
        conn.close()
        
        if not status_row:
            update.message.reply_text("المطعم غير موجود")
            return
            
        status = "شغال ✅" if status_row[0] == 'active' else "واقف ⛔"
        count = log_row[0] if log_row else 0
        total = log_row[1] if log_row else 0
        last = log_row[2] if log_row and log_row[2] else "لا يوجد"
        
        text = f"📊 {name}\nفواتير اليوم: {count}\nالمجموع: {total:,.0f} ريال\nاخر فاتورة: {last}\nالحالة: {status}"
        update.message.reply_text(text)
    except:
        update.message.reply_text("خطأ في عرض التقرير")

def main():
    if not TOKEN or not ADMIN_ID:
        print("ERROR: TOKEN or ADMIN_ID not set")
        return
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("add", add_restaurant))
    dp.add_handler(CommandHandler("stop", stop_restaurant))
    dp.add_handler(CommandHandler("start", start_restaurant))
    dp.add_handler(CommandHandler("devices", devices))
    dp.add_handler(CommandHandler("alert", alert))
    dp.add_handler(CommandHandler("log", log))
    
    print("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
