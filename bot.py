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
)

TOKEN = os.environ.get("TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

SPIN_COOLDOWN = 5

LANG = {
    "ar": {
        "welcome": "أهلاً {name}! 👋\n\n💎 اكسب USDT من السبينات!",
        "profile": "👤 الملف الشخصي",
        "spin_zone": "🎰 منطقة السبين",
        "referrals": "👥 الإحالات",
        "tasks": "📋 المهام",
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
        "menu": "🏠 Menu",
        "spin": "🎰 Spin Now!",
        "withdraw": "💸 Withdraw",
        "lang_btn": "🌐 العربية",
    }
}


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
        tasks_done INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'ar',
        last_spin INTEGER DEFAULT 0
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

    if not exists:
        c.execute("""
        INSERT INTO users
        (user_id, username, spins, balance,
         referred_by, tasks_done, lang, last_spin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user.id,
            user.username,
            1,
            0,
            referred_by,
            0,
            "ar",
            0
        ))

        conn.commit()

    lang = get_lang(user.id, conn)

    conn.close()

    await show_menu(update, context, lang)


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
                tr(lang, "tasks"),
                callback_data="tasks"
            ),
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

    try:
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

    except Exception as e:
        logging.error(e)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()
    c = conn.cursor()

    lang = get_lang(user_id, conn)

    c.execute("""
    SELECT balance, spins, tasks_done
    FROM users
    WHERE user_id=?
    """, (user_id,))

    row = c.fetchone()

    conn.close()

    text = (
        f"👤 {'ملفك الشخصي' if lang=='ar' else 'Your Profile'}\n\n"
        f"💰 Balance: {row[0]:.4f} USDT\n"
        f"🎰 Spins: {row[1]}\n"
        f"📋 Tasks: {row[2]}"
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
    SELECT COUNT(*)
    FROM users
    WHERE referred_by=?
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


async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()

    lang = get_lang(user_id, conn)

    conn.close()

    text = (
        "📋 مهام قادمة قريباً"
        if lang == "ar"
        else "📋 Tasks coming soon"
    )

    keyboard = [
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


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db()
    c = conn.cursor()

    lang = get_lang(user_id, conn)

    c.execute("""
    SELECT balance
    FROM users
    WHERE user_id=?
    """, (user_id,))

    row = c.fetchone()

    conn.close()

    if row[0] < 2:
        text = (
            "❌ تحتاج 2 USDT للسحب"
            if lang == "ar"
            else "❌ You need 2 USDT"
        )

    else:
        text = (
            "💸 أرسل عنوان محفظتك للمشرف"
            if lang == "ar"
            else "💸 Send wallet address to admin"
        )

    keyboard = [
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


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)


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
        CallbackQueryHandler(tasks, pattern="^tasks$")
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

    print("Bot Started...")

    app.run_polling(drop_pending_updates=True)
