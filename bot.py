import sqlite3
import random
import os
import time
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

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

SPIN_COOLDOWN = 5

REFERRAL_SPINS_REWARD = 1
REFERRAL_USDT_REWARD = 0.05

MIN_WITHDRAW = 2.0

# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= LANG =================

LANG = {
    "ar": {
        "welcome": "أهلاً {name}! 👋\n\n💎 اكسب USDT من السبينات!",
        "profile": "👤 الملف الشخصي",
        "spin_zone": "🎰 منطقة السبين",
        "referrals": "👥 الإحالات",
        "tasks": "📋 المهام",
        "leaderboard": "🏆 المتصدرين",
        "daily": "🎁 مكافأة يومية",
        "menu": "🏠 القائمة",
        "spin": "🎰 اسبين الآن!",
        "withdraw": "💸 سحب الرصيد",
        "lang_btn": "🌐 English",
    },

    "en": {
        "welcome": "Hello {name}! 👋\n\n💎 Earn USDT from spins!",
        "profile": "👤 Profile",
        "spin_zone": "🎰 Spin Zone",
        "referrals": "👥 Referrals",
        "tasks": "📋 Tasks",
        "leaderboard": "🏆 Leaderboard",
        "daily": "🎁 Daily Bonus",
        "menu": "🏠 Menu",
        "spin": "🎰 Spin Now!",
        "withdraw": "💸 Withdraw",
        "lang_btn": "🌐 العربية",
    }
}


# ================= HELPERS =================

def tr(lang, key):
    return LANG[lang][key]


def db():
    return sqlite3.connect("bot.db")


def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        spins INTEGER DEFAULT 1,
        balance REAL DEFAULT 0,
        referred_by INTEGER,
        referral_count INTEGER DEFAULT 0,
        tasks_done INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'ar',
        last_spin INTEGER DEFAULT 0,
        last_daily INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS withdraws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        wallet TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)

    conn.commit()
    conn.close()


def get_lang(user_id, conn):
    c = conn.cursor()

    c.execute(
        "SELECT lang FROM users WHERE user_id=?",
        (user_id,)
    )

    row = c.fetchone()

    return row[0] if row else "ar"


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = db()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user.id,)
    )

    exists = c.fetchone()

    referred_by = None

    if context.args and not exists:
        try:
            temp_ref = int(context.args[0])

            if temp_ref != user.id:
                referred_by = temp_ref

        except:
            pass

    # ================= NEW USER =================

    if not exists:

        c.execute("""
        INSERT INTO users
        (user_id, username, spins, balance,
         referred_by, referral_count,
         tasks_done, lang, last_spin, last_daily)

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user.id,
            user.username,
            1,
            0,
            referred_by,
            0,
            0,
            "ar",
            0,
            0
        ))

        conn.commit()

        # 🎁 Referral reward
        if referred_by and referred_by != user.id:

            c.execute("""
            UPDATE users
            SET spins = spins + ?,
                balance = balance + ?,
                referral_count = referral_count + 1
            WHERE user_id = ?
            """, (
                REFERRAL_SPINS_REWARD,
                REFERRAL_USDT_REWARD,
                referred_by
            ))

            conn.commit()

            logging.info(
                f"Referral reward: {referred_by}"
            )

    lang = get_lang(user.id, conn)

    conn.close()

    await show_menu(update, context, lang)


# ================= MENU =================

async def show_menu(update, context, lang=None):

    if update.callback_query:
        user = update.callback_query.from_user
    else:
        user = update.effective_user

    conn = db()

    if not lang:
        lang = get_lang(user.id, conn)

    conn.close()

    keyboard = [

        [
            InlineKeyboardButton(
                tr(lang, "profile"),
                callback_data="profile"
            ),

            InlineKeyboardButton(
                tr(lang, "spin_zone"),
                callback_data="spin_zone"
            ),
        ],

        [
            InlineKeyboardButton(
                tr(lang, "referrals"),
                callback_data="referral"
            ),

            InlineKeyboardButton(
                tr(lang, "leaderboard"),
                callback_data="leaderboard"
            ),
        ],

        [
            InlineKeyboardButton(
                tr(lang, "daily"),
                callback_data="daily_bonus"
            )
        ],

        [
            InlineKeyboardButton(
                tr(lang, "lang_btn"),
                callback_data="toggle_lang"
            )
        ]
    ]

    text = LANG[lang]["welcome"].format(
        name=user.first_name
    )

    if update.callback_query:

        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ================= PROFILE =================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    conn = db()
    c = conn.cursor()

    lang = get_lang(user_id, conn)

    c.execute("""
    SELECT balance, spins, referral_count
    FROM users
    WHERE user_id=?
    """, (user_id,))

    row = c.fetchone()

    conn.close()

    text = (
        f"👤 {'ملفك الشخصي' if lang=='ar' else 'Your Profile'}\n\n"
        f"💰 Balance: {row[0]:.4f} USDT\n"
        f"🎰 Spins: {row[1]}\n"
        f"👥 Referrals: {row[2]}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                tr(lang, "withdraw"),
                callback_data="withdraw"
            )
        ],

        [
            InlineKeyboardButton(
                tr(lang, "menu"),
                callback_data="menu"
            )
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= SPIN ZONE =================

async def spin_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()
    c = conn.cursor()

    lang = get_lang(user_id, conn)

    c.execute("""
    SELECT spins, balance
    FROM users
    WHERE user_id=?
    """, (user_id,))

    row = c.fetchone()

    conn.close()

    text = (
        f"🎰 {'منطقة السبين' if lang=='ar' else 'Spin Zone'}\n\n"
        f"🎰 Spins: {row[0]}\n"
        f"💰 Balance: {row[1]:.4f} USDT"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                tr(lang, "spin"),
                callback_data="spin"
            )
        ],

        [
            InlineKeyboardButton(
                tr(lang, "menu"),
                callback_data="menu"
            )
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= SPIN =================

async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()
    c = conn.cursor()

    lang = get_lang(user_id, conn)

    c.execute("""
    SELECT spins, balance, last_spin
    FROM users
    WHERE user_id=?
    """, (user_id,))

    row = c.fetchone()

    if not row:
        conn.close()
        return

    spins, balance, last_spin = row

    now = int(time.time())

    if now - last_spin < SPIN_COOLDOWN:

        wait_time = SPIN_COOLDOWN - (now - last_spin)

        await query.answer(
            f"⏳ انتظر {wait_time} ثانية"
            if lang == "ar"
            else f"⏳ Wait {wait_time} sec",

            show_alert=True
        )

        conn.close()
        return

    if spins <= 0:

        await query.edit_message_text(
            "❌ لا تملك سبينات"
            if lang == "ar"
            else "❌ No spins left"
        )

        conn.close()
        return

    rewards = [
        (0.20, 3),
        (0.10, 7),
        (0.05, 15),
        (0.01, 25),
        (0.00, 50),
    ]

    rand = random.randint(1, 100)

    cumulative = 0
    prize = 0

    for amount, chance in rewards:

        cumulative += chance

        if rand <= cumulative:
            prize = amount
            break

    c.execute("""
    UPDATE users
    SET spins = spins - 1,
        balance = balance + ?,
        last_spin = ?
    WHERE user_id = ?
    """, (
        prize,
        now,
        user_id
    ))

    conn.commit()

    c.execute("""
    SELECT spins, balance
    FROM users
    WHERE user_id=?
    """, (user_id,))

    updated = c.fetchone()

    conn.close()

    msg = (
        f"🎉 ربحت {prize} USDT"
        if lang == "ar"
        else f"🎉 You won {prize} USDT"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                tr(lang, "spin"),
                callback_data="spin"
            )
        ],

        [
            InlineKeyboardButton(
                tr(lang, "menu"),
                callback_data="menu"
            )
        ]
    ]

    await query.edit_message_text(
        f"{msg}\n\n"
        f"💰 Balance: {updated[1]:.4f} USDT\n"
        f"🎰 Spins: {updated[0]}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= REFERRALS =================

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    bot_username = context.bot.username

    link = f"https://t.me/{bot_username}?start={user_id}"

    conn = db()
    c = conn.cursor()

    lang = get_lang(user_id, conn)

    c.execute("""
    SELECT referral_count
    FROM users
    WHERE user_id=?
    """, (user_id,))

    total_refs = c.fetchone()[0]

    conn.close()

    text = (
        f"👥 {'الإحالات' if lang=='ar' else 'Referrals'}\n\n"
        f"🔗 {link}\n\n"
        f"👤 Total Referrals: {total_refs}"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "🔗 Share",
                url=f"https://t.me/share/url?url={link}"
            )
        ],

        [
            InlineKeyboardButton(
                tr(lang, "menu"),
                callback_data="menu"
            )
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= DAILY BONUS =================

async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()
    c = conn.cursor()

    now = int(time.time())

    c.execute("""
    SELECT last_daily
    FROM users
    WHERE user_id=?
    """, (user_id,))

    last = c.fetchone()[0]

    if now - last < 86400:

        remain = int((86400 - (now - last)) / 3600)

        await query.answer(
            f"⏳ بعد {remain} ساعة"
            ,
            show_alert=True
        )

        conn.close()
        return

    c.execute("""
    UPDATE users
    SET spins = spins + 1,
        last_daily = ?
    WHERE user_id = ?
    """, (
        now,
        user_id
    ))

    conn.commit()
    conn.close()

    await query.edit_message_text(
        "🎁 حصلت على +1 سبين يومي!"
    )


# ================= LEADERBOARD =================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT username, balance
    FROM users
    ORDER BY balance DESC
    LIMIT 10
    """)

    rows = c.fetchall()

    conn.close()

    text = "🏆 TOP USERS\n\n"

    for i, r in enumerate(rows, 1):

        username = r[0] if r[0] else "User"

        text += f"{i}. @{username} — {r[1]:.2f} USDT\n"

    keyboard = [[
        InlineKeyboardButton(
            "🏠 Menu",
            callback_data="menu"
        )
    ]]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= WITHDRAW =================

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT balance
    FROM users
    WHERE user_id=?
    """, (user_id,))

    balance = c.fetchone()[0]

    conn.close()

    if balance < MIN_WITHDRAW:

        await query.edit_message_text(
            f"❌ Minimum withdraw is {MIN_WITHDRAW} USDT"
        )

        return

    context.user_data["withdraw_wait"] = True

    await query.edit_message_text(
        "💸 أرسل عنوان محفظتك الآن"
    )


# ================= HANDLE WALLET =================

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("withdraw_wait"):
        return

    wallet = update.message.text

    user = update.effective_user

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT balance
    FROM users
    WHERE user_id=?
    """, (user.id,))

    balance = c.fetchone()[0]

    c.execute("""
    INSERT INTO withdraws
    (user_id, amount, wallet)
    VALUES (?, ?, ?)
    """, (
        user.id,
        balance,
        wallet
    ))

    conn.commit()
    conn.close()

    context.user_data["withdraw_wait"] = False

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"approve_{user.id}"
            ),

            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"reject_{user.id}"
            )
        ]
    ]

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\n\n"
        f"👤 User: {user.id}\n"
        f"💰 Amount: {balance} USDT\n"
        f"🏦 Wallet:\n{wallet}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text(
        "✅ تم إرسال طلب السحب"
    )


# ================= ADMIN APPROVE =================

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    action, user_id = data.split("_")

    user_id = int(user_id)

    conn = db()
    c = conn.cursor()

    if action == "approve":

        c.execute("""
        UPDATE users
        SET balance = 0
        WHERE user_id=?
        """, (user_id,))

        c.execute("""
        UPDATE withdraws
        SET status='approved'
        WHERE user_id=?
        """, (user_id,))

        conn.commit()

        await context.bot.send_message(
            user_id,
            "✅ تم قبول طلب السحب"
        )

        await query.edit_message_text(
            "✅ Approved"
        )

    elif action == "reject":

        c.execute("""
        UPDATE withdraws
        SET status='rejected'
        WHERE user_id=?
        """, (user_id,))

        conn.commit()

        await context.bot.send_message(
            user_id,
            "❌ تم رفض طلب السحب"
        )

        await query.edit_message_text(
            "❌ Rejected"
        )

    conn.close()


# ================= TOGGLE LANG =================

async def toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()
    c = conn.cursor()

    current = get_lang(user_id, conn)

    new_lang = "en" if current == "ar" else "ar"

    c.execute("""
    UPDATE users
    SET lang=?
    WHERE user_id=?
    """, (
        new_lang,
        user_id
    ))

    conn.commit()
    conn.close()

    await show_menu(update, context, new_lang)


# ================= MENU BUTTON =================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)


# ================= MAIN =================

if __name__ == "__main__":

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(profile, pattern="^profile$")
    )

    app.add_handler(
        CallbackQueryHandler(spin_zone, pattern="^spin_zone$")
    )

    app.add_handler(
        CallbackQueryHandler(spin, pattern="^spin$")
    )

    app.add_handler(
        CallbackQueryHandler(referral, pattern="^referral$")
    )

    app.add_handler(
        CallbackQueryHandler(withdraw, pattern="^withdraw$")
    )

    app.add_handler(
        CallbackQueryHandler(toggle_lang, pattern="^toggle_lang$")
    )

    app.add_handler(
        CallbackQueryHandler(menu, pattern="^menu$")
    )

    app.add_handler(
        CallbackQueryHandler(daily_bonus, pattern="^daily_bonus$")
    )

    app.add_handler(
        CallbackQueryHandler(leaderboard, pattern="^leaderboard$")
    )

    app.add_handler(
        CallbackQueryHandler(admin_actions, pattern="^(approve|reject)_")
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_wallet
        )
    )

    print("Bot Started...")

    app.run_polling(drop_pending_updates=True)
