import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = os.environ.get('TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID'))
NOTIFY_ID = 772765410

DATA_FILE = 'data.json'
ADD_PHONE, ADD_NAME, ADD_DAYS = range(3)

app = Flask(__name__)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"restaurants": {}, "invoices": {}, "owners": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== اوامر البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ADMIN_ID:
        await update.message.reply_text(
            "لوحة تحكم الفواتير\n\n"
            "/add - اضافة مطعم\n"
            "/stop اسم_المطعم - ايقاف مطعم\n"
            "/start اسم_المطعم - تشغيل مطعم\n"
            "/devices اسم_المطعم عدد - توليد config\n"
            "/alert - المطاعم قرب انتهائها\n"
            "/log اسم_المطعم - تقرير مطعم"
        )
    else:
        phone = str(update.message.from_user.id)
        data = load_data()
        data['owners'][phone] = update.message.chat_id
        save_data(data)
        await update.message.reply_text("تم تسجيلك. بتوصلك الفواتير هنا")

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id!= ADMIN_ID: return ConversationHandler.END
    await update.message.reply_text("ارسل رقم صاحب المطعم بدون + مثل: 967771234567")
    return ADD_PHONE

async def add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text.strip()
    await update.message.reply_text("ارسل اسم المطعم")
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("ارسل مدة الاشتراك بالايام مثل: 30")
    return ADD_DAYS

async def add_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
    except:
        await update.message.reply_text("رقم غلط. ارسل المدة بالايام")
        return ADD_DAYS

    data = load_data()
    name = context.user_data['name']
    phone = context.user_data['phone']
    
    if name in data['restaurants']:
        await update.message.reply_text("المطعم موجود مسبقا")
        return ConversationHandler.END

    expire_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    data['restaurants'][name] = {
        "phone": phone,
        "expire": expire_date,
        "active": True,
        "devices": 1,
        "total_invoices": 0,
        "total_amount": 0
    }
    save_data(data)

    await context.bot.send_message(
        chat_id=NOTIFY_ID,
        text=f"مشترك جديد ✅\nالمطعم: {name}\nالجوال: {phone}\nالاشتراك: {days} يوم\nالمبلغ: 20,000 ريال\nينتهي: {expire_date}"
    )

    config = {
        "restaurant_name": name,
        "owner_phone": phone,
        "upload_url": f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}/upload",
        "device_id": "جهاز_1"
    }
    with open(f'config_{name}.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    await update.message.reply_document(
        document=open(f'config_{name}.json', 'rb'),
        caption=f"تم اضافة {name}\n1. حط الملف مع save_invoices.exe\n2. حطه في Startup\n3. خلي صاحب المطعم يرسل /start للبوت"
    )
    os.remove(f'config_{name}.json')
    return ConversationHandler.END

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id!= ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /stop اسم_المطعم")
        return
    name = ' '.join(context.args)
    data = load_data()
    if name not in data['restaurants']:
        await update.message.reply_text("المطعم غير موجود")
        return
    data['restaurants'][name]['active'] = False
    save_data(data)
    await update.message.reply_text(f"تم ايقاف الارسال للمطعم: {name}")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id!= ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /start اسم_المطعم")
        return
    name = ' '.join(context.args)
    data = load_data()
    if name not in data['restaurants']:
        await update.message.reply_text("المطعم غير موجود")
        return
    data['restaurants'][name]['active'] = True
    save_data(data)
    await update.message.reply_text(f"تم تشغيل الارسال للمطعم: {name}")

async def devices_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id!= ADMIN_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("استخدم: /devices اسم_المطعم عدد_الاجهزة")
        return
    count = int(context.args[-1])
    name = ' '.join(context.args[:-1])
    data = load_data()
    if name not in data['restaurants']:
        await update.message.reply_text("المطعم غير موجود")
        return
    
    data['restaurants'][name]['devices'] = count
    save_data(data)
    
    for i in range(1, count + 1):
        config = {
            "restaurant_name": name,
            "owner_phone": data['restaurants'][name]['phone'],
            "upload_url": f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}/upload",
            "device_id": f"جهاز_{i}"
        }
        with open(f'config_{name}_{i}.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        await update.message.reply_document(
            document=open(f'config_{name}_{i}.json', 'rb'),
            caption=f"Config للجهاز رقم {i}"
        )
        os.remove(f'config_{name}_{i}.json')

async def alert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id!= ADMIN_ID: return
    data = load_data()
    found = False
    for name, info in data['restaurants'].items():
        expire = datetime.strptime(info['expire'], "%Y-%m-%d")
        days_left = (expire - datetime.now()).days
        if 0 <= days_left <= 3:
            found = True
            keyboard = [[InlineKeyboardButton("ايقاف المطعم", callback_data=f"stop_{name}")]]
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=f"{name}\nينتهي: {info['expire']}\nباقي: {days_left} يوم",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    if not found:
        await update.message.reply_text("مافي مطاعم قرب انتهائها")

async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id!= ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("استخدم: /log اسم_المطعم")
        return
    name = ' '.join(context.args)
    data = load_data()
    if name not in data['restaurants']:
        await update.message.reply_text("المطعم غير موجود")
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    invoices_today = data['invoices'].get(name, {}).get(today, [])
    total_today = sum(i['amount'] for i in invoices_today)
    last_time = invoices_today[-1]['time'] if invoices_today else "لا يوجد"
    status = "شغال" if data['restaurants'][name]['active'] else "واقف"
    
    msg = f"تقرير {name}\n\nفواتير اليوم: {len(invoices_today)}\nالمجموع: {total_today} ريال\nاخر فاتورة: {last_time}\nالحالة: {status}\n\nاجمالي الفواتير: {data['restaurants'][name]['total_invoices']}\nاجمالي المبلغ: {data['restaurants'][name]['total_amount']} ريال"
    await update.message.reply_text(msg)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith("stop_"):
        name = query.data[5:]
        data = load_data()
        data['restaurants'][name]['active'] = False
        save_data(data)
        await query.edit_message_text(f"تم ايقاف {name}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الالغاء")
    return ConversationHandler.END

# ========== استقبال الفواتير ==========
@app.route('/upload', methods=['POST'])
def upload():
    data = load_data()
    restaurant = request.form.get('restaurant')
    device = request.form.get('device')
    amount = int(request.form.get('amount', 0))
    invoice_num = request.form.get('invoice_num', '0000')
    file = request.files['file']
    
    if restaurant not in data['restaurants']:
        return "Restaurant not found", 404
    
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M")
    if restaurant not in data['invoices']:
        data['invoices'][restaurant] = {}
    if today not in data['invoices'][restaurant]:
        data['invoices'][restaurant][today] = []
    
    data['invoices'][restaurant][today].append({
        "time": time_now,
        "amount": amount,
        "device": device,
        "invoice_num": invoice_num
    })
    data['restaurants'][restaurant]['total_invoices'] += 1
    data['restaurants'][restaurant]['total_amount'] += amount
    save_data(data)
    
    if data['restaurants'][restaurant]['active']:
        phone = data['restaurants'][restaurant]['phone']
        owner_chat_id = data['owners'].get(phone)
        if owner_chat_id:
            caption = f"فاتورة #{invoice_num} - {device} - {time_now} - {amount} ريال"
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendDocument",
                data={"chat_id": owner_chat_id, "caption": caption},
                files={"document": file}
            )
    
    return "OK", 200

# ========== التقارير التلقائية ==========
async def send_daily_reports(app: Application):
    data = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    for name, info in data['restaurants'].items():
        if not info['active']: continue
        invoices = data['invoices'].get(name, {}).get(today, [])
        if not invoices: continue
        
        total = sum(i['amount'] for i in invoices)
        devices_detail = {}
        for inv in invoices:
            dev = inv['device']
            devices_detail[dev] = devices_detail.get(dev, 0) + inv['amount']
        
        msg = f"تقرير يومي - {today}\n\nعدد الفواتير: {len(invoices)}\nالمجموع: {total} ريال\n\nتفصيل الاجهزة:\n"
        for dev, amt in devices_detail.items():
            msg += f"{dev}: {amt} ريال\n"
        
        owner_chat_id = data['owners'].get(info['phone'])
        if owner_chat_id:
            await app.bot.send_message(chat_id=owner_chat_id, text=msg)

async def send_monthly_reports(app: Application):
    data = load_data()
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    for name, info in data['restaurants'].items():
        month_invoices = []
        for day, invs in data['invoices'].get(name, {}).items():
            if day.startswith(last_month):
                month_invoices.extend(invs)
        if not month_invoices: continue
        
        total = sum(i['amount'] for i in month_invoices)
        msg = f"تقرير شهر {last_month}\n\nعدد الفواتير: {len(month_invoices)}\nالمجموع الكلي: {total} ريال"
        
        owner_chat_id = data['owners'].get(info['phone'])
        if owner_chat_id:
            await app.bot.send_message(chat_id=owner_chat_id, text=msg)

async def check_expiry(app: Application):
    data = load_data()
    for name, info in data['restaurants'].items():
        expire = datetime.strptime(info['expire'], "%Y-%m-%d")
        days_left = (expire - datetime.now()).days
        if days_left == 3:
            keyboard = [[InlineKeyboardButton("ايقاف المطعم", callback_data=f"stop_{name}")]]
            await app.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"تنبيه: اشتراك {name} بينتهي بعد 3 ايام\nالتاريخ: {info['expire']}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

def main():
    application = Application.builder().token(TOKEN).build()

    conv_add = ConversationHandler(
        entry_points=[CommandHandler('add', add_start)],
        states={
            ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_days)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_add)
    application.add_handler(CommandHandler('stop', stop_cmd))
    application.add_handler(CommandHandler('start', start_cmd))
    application.add_handler(CommandHandler('devices', devices_cmd))
    application.add_handler(CommandHandler('alert', alert_cmd))
    application.add_handler(CommandHandler('log', log_cmd))
    application.add_handler(CallbackQueryHandler(button_callback))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: application.create_task(check_expiry(application)), 'cron', hour=9)
    scheduler.add_job(lambda: application.create_task(send_daily_reports(application)), 'cron', hour=23, minute=59)
    scheduler.add_job(lambda: application.create_task(send_monthly_reports(application)), 'cron', day=1, hour=9)
    scheduler.start()

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', 5000)),
        webhook_url=f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}/webhook"
    )

if __name__ == '__main__':
    main()
