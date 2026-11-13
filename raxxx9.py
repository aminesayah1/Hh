# language: Python, file: smm_simulation_bot.py, target: Telegram Bot API + SQLite (Simulation Mode)
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# بيانات البوت المدمجة
BOT_TOKEN = "7549956181:AAEA0HGJKjJoejzeObQk3x2uBEXr87y3JNw"
ADMIN_USER_ID = 2082173621

# مراحل المحادثة
SELECT_SERVICE, ENTER_LINK, ENTER_QUANTITY = range(3)

# الخدمات مع الحد الأدنى والأقصى وسعر الوحدة ($)
SERVICES = {
    "ig_followers": {"name": "متابعين انستغرام (تجريبي)", "id": 101, "min": 100, "max": 10000, "rate": 0.005},
    "tt_followers": {"name": "متابعين تيك توك (تجريبي)", "id": 102, "min": 50, "max": 5000, "rate": 0.004},
    "yt_subs": {"name": "مشتركين يوتيوب (تجريبي)", "id": 103, "min": 50, "max": 2000, "rate": 0.02},
}

# إعداد قاعدة البيانات المحلية (SQLite)
def init_db():
    conn = sqlite3.connect("smm_sim_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 10.0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_name TEXT,
            link TEXT,
            quantity INTEGER,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user_balance(user_id: int) -> float:
    conn = sqlite3.connect("smm_sim_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 10.0))
        conn.commit()
        balance = 10.0
    else:
        balance = row[0]
    conn.close()
    return balance

def update_user_balance(user_id: int, amount: float):
    conn = sqlite3.connect("smm_sim_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# محاكاة إرسال الطلب
def simulate_smm_order(user_id: int, service_name: str, link: str, quantity: int) -> int:
    conn = sqlite3.connect("smm_sim_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, service_name, link, quantity, status) VALUES (?, ?, ?, ?, ?)",
        (user_id, service_name, link, quantity, "قيد التنفيذ (تجريبي)")
    )
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id

# محاكاة فحص حالة الطلب
def simulate_check_status(order_id: int) -> dict:
    conn = sqlite3.connect("smm_sim_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT service_name, quantity, status FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"status": row[2], "remains": 0, "service": row[0], "quantity": row[1]}
    return {"error": "رقم الطلب غير موجود"}

# الأوامر الأساسية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_user_balance(user_id)
    
    keyboard = [
        [InlineKeyboardButton(info["name"], callback_data=key)]
        for key, info in SERVICES.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"مرحباً بك في بوت الخدمات الذكية (وضع المحاكاة المجاني).\n"
        f"رصيدك التجريبي الحالي: `{balance:.2f}` $\n\n"
        f"اختر الخدمة المطلوبة للتجربة:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECT_SERVICE

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_user_balance(user_id)
    await update.message.reply_text(f"رصيدك التجريبي الحالي هو: `{balance:.2f}` $", parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الرجاء إدخال رقم الطلب بجانب الأمر.\nمثال: `/status 1`", parse_mode="Markdown")
        return
    
    try:
        order_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("رقم الطلب يجب أن يكون رقماً صحيحاً.")
        return

    res = simulate_check_status(order_id)
    
    if "status" in res:
        await update.message.reply_text(
            f"حالة الطلب التجريبي #{order_id}:\n"
            f"- الخدمة: {res['service']}\n"
            f"- الكمية المطلوبة: {res['quantity']}\n"
            f"- الحالة الحالية: {res['status']}"
        )
    else:
        await update.message.reply_text(res.get("error", "حدث خطأ ما"))

# خطوات المحادثة
async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    service_key = query.data
    svc = SERVICES[service_key]
    
    context.user_data["service_key"] = service_key
    context.user_data["service_name"] = svc["name"]
    context.user_data["min"] = svc["min"]
    context.user_data["max"] = svc["max"]
    context.user_data["rate"] = svc["rate"]
    
    await query.edit_message_text(
        f"تم اختيار: {svc['name']}\n"
        f"(الحد الأدنى: {svc['min']} | الحد الأقصى: {svc['max']})\n\n"
        f"أرسل الآن رابط الحساب الوهمي أو الحقيقي للتجربة:"
    )
    return ENTER_LINK

async def link_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["link"] = update.message.text.strip()
    await update.message.reply_text("أدخل الكمية المطلوبة (ضمن الحدود المسموحة):")
    return ENTER_QUANTITY

async def quantity_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("الرجاء إدخال رقم صحيح فقط:")
        return ENTER_QUANTITY

    quantity = int(text)
    min_q = context.user_data["min"]
    max_q = context.user_data["max"]
    rate = context.user_data["rate"]
    
    if not (min_q <= quantity <= max_q):
        await update.message.reply_text(f"الكمية خارج الحدود. يجب أن تكون بين {min_q} و {max_q}. أعد الإدخال:")
        return ENTER_QUANTITY

    user_id = update.effective_user.id
    total_cost = quantity * rate
    current_balance = get_user_balance(user_id)

    if current_balance < total_cost:
        await update.message.reply_text(f"رصيدك التجريبي غير كافٍ. التكلفة: {total_cost:.2f}$ ورصيدك: {current_balance:.2f}$. تم الإلغاء.")
        return ConversationHandler.END

    service_name = context.user_data["service_name"]
    link = context.user_data["link"]
    
    order_id = simulate_smm_order(user_id, service_name, link, quantity)
    update_user_balance(user_id, total_cost)
    new_balance = get_user_balance(user_id)
    
    await update.message.reply_text(
        f"✅ **[وضع المحاكاة] تم تسجيل الطلب بنجاح!**\n\n"
        f"- رقم الطلب التجريبي: `{order_id}`\n"
        f"- الخدمة: {service_name}\n"
        f"- التكلفة المخصومة: {total_cost:.2f}$\n"
        f"- الرصيد التجريبي المتبقي: {new_balance:.2f}$\n\n"
        f"يمكنك التحقق من حالة الطلب في أي وقت عبر الأمر:\n`/status {order_id}`",
        parse_mode="Markdown"
    )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_SERVICE: [CallbackQueryHandler(service_chosen)],
            ENTER_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, link_received)],
            ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantity_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("status", status_command))
    
    print("بوت المحاكاة التجريبي يعمل الآن...")
    app.run_polling()
