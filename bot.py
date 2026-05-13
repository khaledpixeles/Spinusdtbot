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
    MessageHandler,
    filters,
)

# ================= CONFIG =================

TOKEN = os.environ.get("TOKEN")

ADMIN_ID = 7793635159

CHANNEL_USERNAME = "@Professorprofit10"

TRC20_WALLET = "TEnvHb8kTtR5ZnEvYQbR6J9aFi86edtbiy"

SPIN_COOLDOWN = 5

logging.basicConfig(level=logging.INFO)

# ================= DB =================

def db():
    return sqlite3.connect("new_bot.db")  # ✅ مهم

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        spins INTEGER DEFAULT 1,
        balance REAL DEFAULT 0,
        referred_by INTEGER DEFAULT NULL,
        referral_count INTEGER DEFAULT 0,
        last_spin INTEGER DEFAULT 0,
        last_daily INTEGER DEFAULT 0
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

    conn.commit()
    conn.close()

# ================= FORCE SUB =================

async def check_sub(bot, user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

async def force_sub(update):
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 اشترك بالقناة", url="https://t.me/Professorprofit10")]
    ])
    text = "❌ يجب الاشتراك أولاً"

    if update.message:
        await update.message.reply_text(text, reply_markup=btn)
    else:
        await update.callback_query.message.reply_text(text, reply_markup=btn)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await check_sub(context.bot, user.id):
        await force_sub(update)
        return

    conn = db()
    c = conn.cursor()

    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    exists = c.fetchone()

    ref = None

    if context.args and not exists:
        try:
            r = int(context.args[0])
            if r != user.id:
                c.execute("SELECT user_id FROM users WHERE user_id=?", (r,))
                if c.fetchone():
                    ref = r
        except:
            pass

    if not exists:
        c.execute("""
        INSERT INTO users (user_id, username, spins, balance, referred_by, referral_count, last_spin, last_daily)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user.id, user.username, 1, 0, ref, 0, 0, 0))

        conn.commit()

        if ref:
            c.execute("""
            UPDATE users
            SET spins = spins + 1,
                referral_count = referral_count + 1
            WHERE user_id=?
            """, (ref,))
            conn.commit()

            await context.bot.send_message(
                ADMIN_ID,
                f"👥 إحالة جديدة\nUser: {user.id}\nFrom: {ref}\n🎁 +1 Spin"
            )

    conn.close()
    await menu(update, context)

# ================= MENU =================

async def menu(update, context):
    text = "🏠 Main Menu"

    keyboard = [
        [InlineKeyboardButton("🎰 Spin", callback_data="spin")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("👥 Referrals", callback_data="ref")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="lb")],
        [InlineKeyboardButton("🛒 Shop", callback_data="shop")]
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= SPIN =================

async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("SELECT spins,last_spin FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()

    if not row:
        return

    spins, last = row
    now = int(time.time())

    if now - last < SPIN_COOLDOWN:
        await q.answer("⏳ انتظر", show_alert=True)
        return

    if spins <= 0:
        await q.edit_message_text("❌ لا يوجد سبينات")
        return

    rewards = [
        (0.10, 1),
        (0.05, 6),
        (0.02, 15),
        (0.01, 25),
        (0.00, 53),
    ]

    r = random.randint(1, 100)
    total = 0
    win = 0

    for a, cst in rewards:
        total += cst
        if r <= total:
            win = a
            break

    c.execute("""
    UPDATE users
    SET spins=spins-1,
        balance=balance+?,
        last_spin=?
    WHERE user_id=?
    """, (win, now, uid))

    conn.commit()

    c.execute("SELECT spins,balance FROM users WHERE user_id=?", (uid,))
    u = c.fetchone()

    conn.close()

    await q.edit_message_text(f"🎉 ربحت {win}\n💰 {u[1]:.4f}\n🎰 {u[0]}")

# ================= PROFILE =================

async def profile(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("SELECT balance,spins,referral_count FROM users WHERE user_id=?", (uid,))
    u = c.fetchone()

    conn.close()

    text = f"""👤 Profile

💰 Balance: {u[0]:.4f}
🎰 Spins: {u[1]}
👥 Referrals: {u[2]}
"""

    await q.edit_message_text(text)

# ================= REFERRALS =================

async def referral(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    link = f"https://t.me/{context.bot.username}?start={uid}"

    conn = db()
    c = conn.cursor()

    c.execute("SELECT referral_count FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()[0]

    conn.close()

    text = f"""👥 Referrals

🔗 {link}
👤 Total: {r}
"""

    await q.edit_message_text(text)

# ================= LEADERBOARD =================

async def leaderboard(update, context):
    q = update.callback_query
    await q.answer()

    conn = db()
    c = conn.cursor()

    c.execute("SELECT username,balance FROM users ORDER BY balance DESC LIMIT 10")
    rows = c.fetchall()

    conn.close()

    text = "🏆 TOP USERS\n\n"

    for i, r in enumerate(rows, 1):
        name = r[0] or "User"
        text += f"{i}. @{name} - {r[1]:.4f}\n"

    await q.edit_message_text(text)

# ================= SHOP =================

async def shop(update, context):
    q = update.callback_query
    await q.answer()

    text = """🛒 Shop

10 Spins = 1 USDT
50 Spins = 4 USDT
"""

    keyboard = [
        [InlineKeyboardButton("Buy 10", callback_data="buy10")],
        [InlineKeyboardButton("Buy 50", callback_data="buy50")]
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

    c.execute("""
    INSERT INTO shop_orders(user_id,spins,usdt)
    VALUES(?,?,?)
    """, (uid, spins, price))

    conn.commit()
    conn.close()

    await context.bot.send_message(
        ADMIN_ID,
        f"🛒 Order\nUser: {uid}\nSpins: {spins}\nUSDT: {price}\nWallet: {TRC20_WALLET}"
    )

    await q.edit_message_text("⏳ تم إرسال الطلب")

# ================= HANDLERS =================

async def menu_btn(update, context):
    await menu(update, context)

# ================= MAIN =================

if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(spin, pattern="^spin$"))
    app.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(referral, pattern="^ref$"))
    app.add_handler(CallbackQueryHandler(leaderboard, pattern="^lb$"))
    app.add_handler(CallbackQueryHandler(shop, pattern="^shop$"))
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy"))
    app.add_handler(CallbackQueryHandler(menu_btn, pattern="^menu$"))

    print("Bot Running...")
    app.run_polling()
