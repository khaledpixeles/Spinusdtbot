import sqlite3
import random
import os
import time
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 7793635159

CHANNEL_USERNAME = "@Professorprofit10"
CHANNEL_LINK = "https://t.me/Professorprofit10"

logging.basicConfig(level=logging.INFO)

# ================= DB =================

def db():
    return sqlite3.connect("new_bot.db")

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        spins INTEGER DEFAULT 1,
        balance REAL DEFAULT 0,
        vip INTEGER DEFAULT 0,
        ref_by INTEGER DEFAULT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        network TEXT,
        wallet TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS shop_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        spins INTEGER,
        price REAL,
        status TEXT DEFAULT 'pending'
    )
    """)

    conn.commit()
    conn.close()

# ================= SUB CHECK =================

async def is_joined(bot, user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


async def force_sub(update):
    keyboard = [
        [InlineKeyboardButton("📢 اشتراك", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✔ تحقق", callback_data="check_sub")]
    ]

    text = "❌ يجب الاشتراك أولاً"

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= START =================

async def start(update, context):
    user = update.effective_user

    if not await is_joined(context.bot, user.id):
        await force_sub(update)
        return

    conn = db()
    c = conn.cursor()

    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username) VALUES (?,?)", (user.id, user.username))
        conn.commit()

    conn.close()
    await menu(update, context)

# ================= MENU =================

async def menu(update, context):
    keyboard = [
        [InlineKeyboardButton("🎰 Spin", callback_data="spin")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("👥 Referrals", callback_data="ref")],
        [InlineKeyboardButton("👑 VIP", callback_data="vip")],
        [InlineKeyboardButton("🛒 Shop", callback_data="shop")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")]
    ]

    text = "🏠 Main Menu"

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= PROFILE =================

async def profile(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("SELECT spins,balance,vip FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()

    conn.close()

    text = f"""👤 Profile

💰 Balance: {row[1]:.4f}
🎰 Spins: {row[0]}
👑 VIP: {'YES' if row[2] else 'NO'}"""

    await q.edit_message_text(text)

# ================= REFERRALS =================

async def referrals(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    bot_username = context.bot.username

    link = f"https://t.me/{bot_username}?start={uid}"

    conn = db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users WHERE ref_by=?", (uid,))
    count = c.fetchone()[0]

    conn.close()

    text = f"""👥 Referrals

🔗 {link}
👤 Total: {count}"""

    await q.edit_message_text(text)

# ================= CHECK SUB =================

async def check_sub(update, context):
    q = update.callback_query
    await q.answer()

    if await is_joined(context.bot, q.from_user.id):
        await q.edit_message_text("✅ تم التحقق")
    else:
        await q.answer("❌ لم تشترك", show_alert=True)

# ================= SPIN =================

async def spin(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("SELECT spins,vip FROM users WHERE user_id=?", (uid,))
    user = c.fetchone()

    spins, vip = user

    if spins <= 0:
        await q.edit_message_text("❌ لا يوجد سبينات")
        return

    rewards = [
        (0.10, 5),
        (0.05, 10),
        (0.02, 20),
        (0.00, 65),
    ]

    r = random.randint(1, 100)
    total = 0
    win = 0

    for a, p in rewards:
        total += p
        if r <= total:
            win = a
            break

    if vip:
        win *= 1.2

    c.execute("""
    UPDATE users
    SET spins=spins-1,
        balance=balance+?
    WHERE user_id=?
    """, (win, uid))

    conn.commit()

    c.execute("SELECT spins,balance FROM users WHERE user_id=?", (uid,))
    u = c.fetchone()

    conn.close()

    await q.edit_message_text(f"🎰 {win:.4f}\n💰 {u[1]:.4f}\n🎰 {u[0]}")

# ================= WITHDRAW =================

async def withdraw(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    keyboard = [
        [InlineKeyboardButton("TRC20", callback_data="net_trc")],
        [InlineKeyboardButton("BEP20", callback_data="net_bep")]
    ]

    await q.edit_message_text("💸 اختر الشبكة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def network(update, context):
    q = update.callback_query
    await q.answer()

    net = "TRC20" if q.data == "net_trc" else "BEP20"

    uid = q.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    bal = c.fetchone()[0]

    conn.close()

    if bal <= 0:
        await q.edit_message_text("❌ لا يوجد رصيد")
        return

    wallet = "PENDING_INPUT"

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO withdrawals (user_id,amount,network,wallet)
    VALUES (?,?,?,?)
    """, (uid, bal, net, wallet))

    conn.commit()
    conn.close()

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 سحب جديد\nUser:{uid}\nAmount:{bal}\nNetwork:{net}"
    )

    await q.edit_message_text("⏳ تم إرسال الطلب")

# ================= SHOP =================

async def shop(update, context):
    q = update.callback_query
    await q.answer()

    text = "🛒 Shop\n10 Spins = 1$\n50 Spins = 4$"

    keyboard = [
        [InlineKeyboardButton("10 Spins", callback_data="buy10")],
        [InlineKeyboardButton("50 Spins", callback_data="buy50")]
    ]

    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def buy(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    spins = 10 if q.data == "buy10" else 50
    price = 1 if spins == 10 else 4

    conn = db()
    c = conn.cursor()

    c.execute("UPDATE users SET spins=spins+? WHERE user_id=?", (spins, uid))
    conn.commit()
    conn.close()

    await q.edit_message_text("✅ تم إضافة السبينات")

# ================= ADMIN =================

async def admin(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    conn = db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]

    c.execute("SELECT SUM(balance) FROM users")
    bal = c.fetchone()[0] or 0

    conn.close()

    await update.message.reply_text(f"""👑 Admin

Users: {users}
Balance: {bal:.2f}""")

# ================= HANDLERS =================

if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(check_sub, pattern="check_sub"))
    app.add_handler(CallbackQueryHandler(spin, pattern="spin"))
    app.add_handler(CallbackQueryHandler(profile, pattern="profile"))
    app.add_handler(CallbackQueryHandler(referrals, pattern="ref"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="withdraw"))

    app.add_handler(CallbackQueryHandler(network, pattern="net_"))
    app.add_handler(CallbackQueryHandler(shop, pattern="shop"))
    app.add_handler(CallbackQueryHandler(buy, pattern="buy"))

    print("Bot Running...")
    app.run_polling()
