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
        "lang_btn": "🌐 العربية",
    }
}


def tr(lang, key):
    return LANG[lang][key]


def db_connection():
    return sqlite3.connect("bot.db")


def init_db():
    conn = db_connection()
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        spins INTEGER DEFAULT 1,
        balance REAL DEFAULT 0,
        referred_by INTEGER,
        referral_counted INTEGER DEFAULT 0,
        tasks_done INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'ar',
        last_spin INTEGER DEFAULT 0
    )
    ''')

    conn.commit()
    conn.close()



def get_lang(user_id, conn):
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()

    return row[0] if row else "ar"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = db_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
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
        c.execute(
            """
            INSERT INTO users
            (user_id, username, spins, balance, referred_by,
             referral_counted, tasks_done, lang, last_spin)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                user.id,
                user.username,
                1,
                0,
                referred_by,
                0,
                0,
                'ar',
                0
            )
        )

        conn.commit()

    lang = get_lang(user.id, conn)

    conn.close()

    await show_menu(update, context, lang)


async def show_menu(update, context, lang=None):
    if update.callback_query:
        user = update.callback_query.from_user
    else:
        user = update.effective_user

    conn = db_connection()

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
        ],
    ]

    text = LANG[lang]["welcome"].format(name=user.first_name)

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


async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db_connection()
    c = conn.cursor()

    lang = get_lang(user_id, conn)

    c.execute(
        "SELECT spins, balance, last_spin FROM users WHERE user_id=?",
        (user_id,)
    )

    row = c.fetchone()

    if not row:
        conn.close()
        return

    spins, balance, last_spin = row

    now = int(time.time())

    if now - last_spin < SPIN_COOLDOWN:
        wait_time = SPIN_COOLDOWN - (now - last_spin)

        await query.answer(
            f"⏳ انتظر {wait_time} ثانية" if lang == "ar"
            else f"⏳ Wait {wait_time} seconds",
            show_alert=True
        )

        conn.close()
        return

    if spins <= 0:
        await query.edit_message_text(
            "❌ لا تملك سبينات" if lang == "ar"
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

    c.execute(
        """
        UPDATE users
        SET spins = spins - 1,
            balance = balance + ?,
            last_spin = ?
        WHERE user_id = ?
        """,
        (prize, now, user_id)
    )

    conn.commit()

    c.execute(
        "SELECT spins, balance FROM users WHERE user_id=?",
        (user_id,)
    )

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

    try:
        await query.edit_message_text(
            f"{msg}\n\n"
            f"💰 Balance: {updated[1]:.4f} USDT\n"
            f"🎰 Spins: {updated[0]}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(e)


async def toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    conn = db_connection()
    c = conn.cursor()

    current = get_lang(user_id, conn)

    new_lang = "en" if current == "ar" else "ar"

    c.execute(
        "UPDATE users SET lang=? WHERE user_id=?",
        (new_lang, user_id)
    )

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
        CallbackQueryHandler(spin, pattern="^spin$")
    )

    app.add_handler(
        CallbackQueryHandler(toggle_lang, pattern="^toggle_lang$")
    )

    app.add_handler(
        CallbackQueryHandler(menu, pattern="^menu$")
    )

    app.run_polling(drop_pending_updates=True)
