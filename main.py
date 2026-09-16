import os
import sqlite3
import json
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# ======== الاعدادات ========
TOKEN = os.environ.get('TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID'))
YOUR_NUMBER = 772765410 # رقمك للتنبيهات
SUBSCRIPTION_PRICE = 20000

logging.basicConfig(level=logging.INFO)

# حالات المحادثة
OWNER_ID, RESTAURANT_NAME, SUB_DAYS = range(3)

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

# ======== الكيبورد الرئيسي ========
def main_menu_keyboard():
    keyboard = [
        [KeyboardButton("➕ اضافة مطعم")],
        [KeyboardButton("📋 كل المطاعم"), KeyboardButton("⚠️ التنبيهات")],
        [KeyboardButton("📊 تقرير سريع")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("❌ الغاء")]], resize_keyboard=True)

# ======== البداية ========
def start(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    update.message.reply_text(
        "اهلا بك في لوحة تحكم الفواتير ✅\n\nاختر من القائمة تحت:",
        reply_markup=main_menu_keyboard()
    )

# ======== اضافة مطعم خطوة خطوة ========
def add_restaurant_start(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    update.message.reply_text(
        "ارسل رقم صاحب المطعم مع مفتاح الدولة\nمثال: 967771234567",
        reply_markup=cancel_keyboard()
    )
    return OWNER_ID

def get_owner_id(update: Update, context: CallbackContext):
    if update.message.text == "❌ الغاء":
        update.message.reply_text("تم الالغاء", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    
    context.user_data['owner_id'] = update.message.text.strip()
    update.message.reply_text(
        "تمام. الحين ارسل اسم المطعم\nمثال: رشيد العبيدي",
        reply_markup=cancel_keyboard()
    )
    return RESTAURANT_NAME

def get_restaurant_name(update: Update, context: CallbackContext):
    if update.message.text == "❌ الغاء":
        update.message.reply_text("تم الالغاء", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    
    context.user_data['restaurant_name'] = update.message.text.strip()
    update.message.reply_text(
        "تمام. الحين ارسل عدد ايام الاشتراك\nمثال: 30",
        reply_markup=cancel_keyboard()
    )
    return SUB_DAYS

def get_sub_days(update: Update, context: CallbackContext):
    if update.message.text == "❌ الغاء":
        update.message.reply_text("تم الالغاء", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    
    try:
        days = int(update.message.text.strip())
        owner_id = context.user_data['owner_id']
        name = context.user_data['restaurant_name']
        
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

        update.message.reply_document(
            document=bytes(config_str, 'utf-8'),
            filename=f"config_{name}.json",
            caption=f"✅ تم اضافة {name}\nينتهي: {end_date.date()}",
            reply_markup=main_menu_keyboard()
        )

        # تنبيه لك على رقمك 772765410
        alert_text = f"🔔 اشتراك جديد!\nالمطعم: {name}\nالمالك: {owner_id}\nالمبلغ: {SUBSCRIPTION_PRICE:,} ريال\nالمدة: {days} يوم"
        context.bot.send_message(chat_id=ADMIN_ID, text=alert_text)

    except Exception as e:
        update.message.reply_text(f"خطأ: {e}\nتأكد من البيانات", reply_markup=main_menu_keyboard())
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("تم الالغاء", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

# ======== عرض كل المطاعم ========
def list_restaurants(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    
    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute("SELECT name, status, end_date FROM restaurants ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        update.message.reply_text("مافي مطاعم مضافة", reply_markup=main_menu_keyboard())
        return
    
    keyboard = []
    text = "📋 كل المطاعم:\n\n"
    for name, status, end_date in rows:
        end = datetime.datetime.fromisoformat(end_date)
        days_left = (end - datetime.datetime.now()).days
        status_emoji = "✅" if status == 'active' else "⛔"
        text += f"{status_emoji} {name} - باقي {days_left} يوم\n"
        keyboard.append([InlineKeyboardButton(f"⚙️ {name}", callback_data=f"manage_{name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)

# ======== ادارة مطعم واحد ========
def manage_restaurant(update: Update, context: CallbackContext):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    query.answer()
    
    name = query.data.replace("manage_", "")
    
    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute("SELECT status, end_date, owner_id FROM restaurants WHERE name=?", (name,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        query.edit_message_text("المطعم محذوف")
        return
    
    status, end_date, owner_id = row
    end = datetime.datetime.fromisoformat(end_date)
    days_left = (end - datetime.datetime.now()).days
    status_text = "شغال ✅" if status == 'active' else "واقف ⛔"
    
    keyboard = []
    if status == 'active':
        keyboard.append([InlineKeyboardButton("⛔ ايقاف الارسال", callback_data=f"stop_{name}")])
    else:
        keyboard.append([InlineKeyboardButton("✅ تشغيل الارسال", callback_data=f"start_{name}")])
    
    keyboard.append([InlineKeyboardButton("📊 عرض التقرير", callback_data=f"log_{name}")])
    keyboard.append([InlineKeyboardButton("➕ اضافة جهاز", callback_data=f"devices_{name}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_list")])
    
    text = f"⚙️ {name}\n\nالحالة: {status_text}\nالمالك: {owner_id}\nينتهي: {end.date()}\nباقي: {days_left} يوم"
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ======== ايقاف / تشغيل ========
def stop_restaurant(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    name = query.data.replace("stop_", "")
    
    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute("UPDATE restaurants SET status='stopped' WHERE name=?", (name,))
    conn.commit()
    conn.close()
    
    query.answer(f"تم ايقاف {name}", show_alert=True)
    # نرجع لنفس صفحة الادارة
    context.user_data['callback_data'] = f"manage_{name}"
    manage_restaurant(update, context)

def start_restaurant(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    name = query.data.replace("start_", "")
    
    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute("UPDATE restaurants SET status='active' WHERE name=?", (name,))
    conn.commit()
    conn.close()
    
    query.answer(f"تم تشغيل {name}", show_alert=True)
    context.user_data['callback_data'] = f"manage_{name}"
    manage_restaurant(update, context)

# ======== التقرير ========
def show_log(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    name = query.data.replace("log_", "")
    
    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute("SELECT status FROM restaurants WHERE name=?", (name,))
    status_row = c.fetchone()
    c.execute("SELECT count_today, total_today, last_invoice_time FROM invoices_log WHERE restaurant_name=?", (name,))
    log_row = c.fetchone()
    conn.close()
    
    status = "شغال ✅" if status_row[0] == 'active' else "واقف ⛔"
    count = log_row[0] if log_row else 0
    total = log_row[1] if log_row else 0
    last = log_row[2] if log_row and log_row[2] else "لا يوجد"
    
    text = f"📊 تقرير {name}\n\nفواتير اليوم: {count}\nالمجموع: {total:,.0f} ريال\nاخر فاتورة: {last}\nالحالة: {status}"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_{name}")]]
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ======== التنبيهات ========
def show_alerts(update: Update, context: CallbackContext):
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
        update.message.reply_text("✅ كل الاشتراكات تمام", reply_markup=main_menu_keyboard())
        return
    
    text = "⚠️ مطاعم قرب ينتهي اشتراكها:\n\n"
    keyboard = []
    for name, end_date in rows:
        end = datetime.datetime.fromisoformat(end_date)
        days_left = (end - today).days
        text += f"• {name} - باقي {days_left} يوم\n"
        keyboard.append([InlineKeyboardButton(f"⚙️ ادارة {name}", callback_data=f"manage_{name}")])
    
    update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ======== تقرير سريع ========
def quick_report(update: Update, context: CallbackContext):
    conn = sqlite3.connect('restaurants.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM restaurants WHERE status='active'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM restaurants WHERE status='stopped'")
    stopped = c.fetchone()[0]
    c.execute("SELECT SUM(count_today) FROM invoices_log")
    total_invoices = c.fetchone()[0] or 0
    c.execute("SELECT SUM(total_today) FROM invoices_log")
    total_amount = c.fetchone()[0] or 0
    conn.close()
    
    text = f"📊 تقرير سريع\n\nمطاعم شغالة: {active}\nمطاعم واقفة: {stopped}\nفواتير اليوم الكل: {total_invoices}\nالمجموع الكل: {total_amount:,.0f} ريال"
    update.message.reply_text(text, reply_markup=main_menu_keyboard())

def back_to_list(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    # نحولها لرسالة عادية عشان نشغل list_restaurants
    query.message.reply_text("جاري التحميل...")
    list_restaurants(query, context)

def main():
    if not TOKEN or not ADMIN_ID:
        print("ERROR: TOKEN or ADMIN_ID not set")
        return
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # محادثة اضافة مطعم
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^➕ اضافة مطعم$'), add_restaurant_start)],
        states={
            OWNER_ID: [MessageHandler(Filters.text & ~Filters.command, get_owner_id)],
            RESTAURANT_NAME: [MessageHandler(Filters.text & ~Filters.command, get_restaurant_name)],
            SUB_DAYS: [MessageHandler(Filters.text & ~Filters.command, get_sub_days)],
        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(Filters.regex('^❌ الغاء$'), cancel)]
    )
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.regex('^📋 كل المطاعم$'), list_restaurants))
    dp.add_handler(MessageHandler(Filters.regex('^⚠️ التنبيهات$'), show_alerts))
    dp.add_handler(MessageHandler(Filters.regex('^📊 تقرير سريع$'), quick_report))
    
    dp.add_handler(CallbackQueryHandler(manage_restaurant, pattern='^manage_'))
    dp.add_handler(CallbackQueryHandler(stop_restaurant, pattern='^stop_'))
    dp.add_handler(CallbackQueryHandler(start_restaurant, pattern='^start_'))
    dp.add_handler(CallbackQueryHandler(show_log, pattern='^log_'))
    dp.add_handler(CallbackQueryHandler(back_to_list, pattern='^back_to_list'))
    
    print("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
