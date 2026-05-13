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

SPIN_COOLDOWN = 5

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
        last_spin INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS shop_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        spins INTEGER,
        usdt REAL,
        status TEXT DEFAULT 'pending'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        status TEXT DEFAULT 'pending'
    )
    """)

    conn.commit()
    conn.close()

# ================= SUB =================

async def is_joined(bot, user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


async def force_sub(update):
    keyboard = [
        [InlineKeyboardButton("📢 الاشتراك", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✔ تحقق", callback_data="check_sub")]
    ]

    text = "❌ اشترك في القناة أولاً"

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
        [InlineKeyboardButton("👑 VIP", callback_data="vip")],
        [InlineKeyboardButton("🛒 Shop", callback_data="shop")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")]
    ]

    text = "🏠 Main Menu"

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= SPIN =================

async def spin(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("SELECT spins, vip FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()

    if not row:
        return

    spins, vip = row

    if spins <= 0:
        await q.edit_message_text("❌ لا يوجد سبينات")
        return

    rewards = [
        (0.20, 3),
        (0.10, 7),
        (0.05, 15),
        (0.01, 25),
        (0.00, 50),
    ]

    r = random.randint(1, 100)
    total = 0
    win = 0

    for a, cst in rewards:
        total += cst
        if r <= total:
            win = a
            break

    if vip:
        win *= 1.2

    c.execute("""
    UPDATE users
    SET spins=spins-1,
        balance=balance+?,
        last_spin=?
    WHERE user_id=?
    """, (win, int(time.time()), uid))

    conn.commit()

    c.execute("SELECT spins,balance FROM users WHERE user_id=?", (uid,))
    u = c.fetchone()

    conn.close()

    await q.edit_message_text(f"🎉 ربحت {win:.4f}\n💰 {u[1]:.4f}\n🎰 {u[0]}")

# ================= VIP =================

async def vip(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("SELECT vip FROM users WHERE user_id=?", (uid,))
    vip = c.fetchone()[0]

    conn.close()

    text = "👑 VIP مفعل" if vip else "👑 VIP = تواصل مع الأدمن للتفعيل"

    await q.edit_message_text(text)

# ================= SHOP =================

async def shop(update, context):
    q = update.callback_query
    await q.answer()

    text = "🛒 Shop\n\n10 Spins = 1 USDT\n50 Spins = 4 USDT"

    keyboard = [
        [InlineKeyboardButton("10 Spins", callback_data="buy10")],
        [InlineKeyboardButton("50 Spins", callback_data="buy50")]
    ]

    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= BUY =================

async def buy(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    spins = 10 if q.data == "buy10" else 50
    price = 1 if spins == 10 else 4

    conn = db()
    c = conn.cursor()

    c.execute("INSERT INTO shop_orders (user_id,spins,usdt) VALUES (?,?,?)", (uid, spins, price))
    conn.commit()

    conn.close()

    await context.bot.send_message(
        ADMIN_ID,
        f"🛒 طلب شراء\nUser: {uid}\nSpins: {spins}\nUSDT: {price}"
    )

    await q.edit_message_text("⏳ تم إرسال الطلب")

# ================= WITHDRAW =================

async def withdraw(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    bal = c.fetchone()[0]

    if bal <= 0:
        await q.edit_message_text("❌ لا يوجد رصيد")
        return

    c.execute("INSERT INTO withdrawals (user_id,amount) VALUES (?,?)", (uid, bal))
    conn.commit()

    conn.close()

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 سحب\nUser: {uid}\nAmount: {bal:.4f}"
    )

    await q.edit_message_text("⏳ تم إرسال طلب السحب")

# ================= ADMIN =================

async def admin(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    conn = db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]

    c.execute("SELECT SUM(balance) FROM users")
    total = c.fetchone()[0] or 0

    conn.close()

    await update.message.reply_text(
        f"👑 Admin Panel\nUsers: {users}\nBalance: {total:.2f}"
    )

# ================= MAIN =================

if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(spin, pattern="^spin$"))
    app.add_handler(CallbackQueryHandler(vip, pattern="^vip$"))
    app.add_handler(CallbackQueryHandler(shop, pattern="^shop$"))
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))

    app.add_handler(CommandHandler("menu", menu))

    print("Bot Running...")
    app.run_polling()
