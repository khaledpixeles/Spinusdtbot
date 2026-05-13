import sqlite3
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")

LANG = {
    "ar": {
        "welcome": "أهلاً {name}! 👋\n\n💎 اكسب USDT حقيقي من السبينات!",
        "lang_btn": "🌐 English",
    },
    "en": {
        "welcome": "Hello {name}! 👋\n\n💎 Earn real USDT from spins!",
        "lang_btn": "🌐 العربية",
    }
}

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        spins INTEGER DEFAULT 3,
        balance REAL DEFAULT 0,
        referred_by INTEGER,
        referral_counted INTEGER DEFAULT 0,
        tasks_done INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'ar'
    )''')
    conn.commit()
    conn.close()

def get_lang(user_id, conn):
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row[0] if row else "ar"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    exists = c.fetchone()
    referred_by = None
    if context.args and not exists:
        try:
            referred_by = int(context.args[0])
        except:
            pass
    if not exists:
        c.execute("INSERT INTO users VALUES (?,?,3,0,?,0,0,'ar')",
                  (user.id, user.username, referred_by))
        conn.commit()
    lang = get_lang(user.id, conn)
    conn.close()
    await show_menu(update, context, lang)

async def show_menu(update, context, lang=None):
    if update.callback_query:
        user = update.callback_query.from_user
    else:
        user = update.effective_user
    conn = sqlite3.connect("bot.db")
    if not lang:
        lang = get_lang(user.id, conn)
    conn.close()
    t = LANG[lang]
    keyboard = [
        [
            InlineKeyboardButton("👤 الملف الشخصي" if lang=="ar" else "👤 Profile", callback_data="profile"),
            InlineKeyboardButton("🎰 منطقة السبين" if lang=="ar" else "🎰 Spin Zone", callback_data="spin_zone"),
        ],
        [
            InlineKeyboardButton("👥 الإحالات" if lang=="ar" else "👥 Referrals", callback_data="referral"),
            InlineKeyboardButton("📋 المهام" if lang=="ar" else "📋 Tasks", callback_data="tasks"),
        ],
        [InlineKeyboardButton(t["lang_btn"], callback_data="toggle_lang")],
    ]
    text = t["welcome"].format(name=user.first_name)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    lang = get_lang(user_id, conn)
    c.execute("SELECT balance, spins, tasks_done FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if lang == "ar":
        text = (f"👤 ملفك الشخصي\n\n"
                f"💰 الرصيد: {row[0]:.4f} USDT\n"
                f"🎰 السبينات: {row[1]}\n"
                f"📋 المهام المنجزة: {row[2]}\n\n"
                f"━━━━━━━━━━━━━━\n"
                f"💸 طرق السحب:\n• USDT TRC20\n• USDT BEP20\n\n"
                f"⚠️ الحد الأدنى للسحب: 2 USDT\n"
                f"⏱ وقت التحويل: خلال 24 ساعة")
        keyboard = [
            [InlineKeyboardButton("💸 سحب الرصيد", callback_data="withdraw")],
            [InlineKeyboardButton("🏠 القائمة", callback_data="menu")],
        ]
    else:
        text = (f"👤 Your Profile\n\n"
                f"💰 Balance: {row[0]:.4f} USDT\n"
                f"🎰 Spins: {row[1]}\n"
                f"📋 Tasks Done: {row[2]}\n\n"
                f"━━━━━━━━━━━━━━\n"
                f"💸 Withdrawal Methods:\n• USDT TRC20\n• USDT BEP20\n\n"
                f"⚠️ Minimum withdrawal: 2 USDT\n"
                f"⏱ Transfer time: within 24 hours")
        keyboard = [
            [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
            [InlineKeyboardButton("🏠 Menu", callback_data="menu")],
        ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def spin_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    lang = get_lang(user_id, conn)
    c.execute("SELECT spins, balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if lang == "ar":
        text = (f"🎰 منطقة السبين\n\n"
                f"🎰 سبيناتك: {row[0]}\n"
                f"💰 رصيدك: {row[1]:.4f} USDT\n\n"
                f"━━━━━━━━━━━━━━\n"
                f"🎯 نسب الفوز:\n"
                f"🎉 0.2 USDT — 3%\n"
                f"✨ 0.1 USDT — 7%\n"
                f"⭐ 0.05 USDT — 15%\n"
                f"🌟 0.01 USDT — 25%\n"
                f"😔 لا شيء — 50%")
        keyboard = [
            [InlineKeyboardButton("🎰 اسبين الآن!", callback_data="spin")],
            [InlineKeyboardButton("🏠 القائمة", callback_data="menu")],
        ]
    else:
        text = (f"🎰 Spin Zone\n\n"
                f"🎰 Your Spins: {row[0]}\n"
                f"💰 Balance: {row[1]:.4f} USDT\n\n"
                f"━━━━━━━━━━━━━━\n"
                f"🎯 Win Chances:\n"
                f"🎉 0.2 USDT — 3%\n"
                f"✨ 0.1 USDT — 7%\n"
                f"⭐ 0.05 USDT — 15%\n"
                f"🌟 0.01 USDT — 25%\n"
                f"😔 No win — 50%")
        keyboard = [
            [InlineKeyboardButton("🎰 Spin Now!", callback_data="spin")],
            [InlineKeyboardButton("🏠 Menu", callback_data="menu")],
        ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    lang = get_lang(user_id, conn)
    c.execute("SELECT spins, balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row or row[0] <= 0:
        keyboard = [[InlineKeyboardButton("📋 مهام" if lang=="ar" else "📋 Tasks", callback_data="tasks")]]
        await query.edit_message_text(
            "❌ ليس لديك سبينات!\n📋 نفّذ مهام للحصول على سبينات" if lang=="ar"
            else "❌ You have no spins!\n📋 Complete tasks to get spins",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        conn.close()
        return
    results_ar = [
        ("🎉 ربحت 0.2 USDT!", 0.20, 3),
        ("✨ ربحت 0.1 USDT!", 0.10, 7),
        ("⭐ ربحت 0.05 USDT!", 0.05, 15),
        ("🌟 ربحت 0.01 USDT!", 0.01, 25),
        ("😔 لم تربح شيئاً", 0.00, 50),
    ]
    results_en = [
        ("🎉 Won 0.2 USDT!", 0.20, 3),
        ("✨ Won 0.1 USDT!", 0.10, 7),
        ("⭐ Won 0.05 USDT!", 0.05, 15),
        ("🌟 Won 0.01 USDT!", 0.01, 25),
        ("😔 No win this time", 0.00, 50),
    ]
    results = results_ar if lang == "ar" else results_en
    rand = random.randint(1, 100)
    cumulative = 0
    prize = 0.0
    message = ""
    for result in results:
        cumulative += result[2]
        if rand <= cumulative:
            message = result[0]
            prize = result[1]
            break
    c.execute("UPDATE users SET spins=spins-1, balance=balance+? WHERE user_id=?",
              (prize, user_id))
    conn.commit()
    c.execute("SELECT spins, balance FROM users WHERE user_id=?", (user_id,))
    updated = c.fetchone()
    conn.close()
    keyboard = [
        [InlineKeyboardButton("🎰 سبين مجدداً" if lang=="ar" else "🎰 Spin Again", callback_data="spin")],
        [InlineKeyboardButton("🏠 القائمة" if lang=="ar" else "🏠 Menu", callback_data="menu")],
    ]
    await query.edit_message_text(
        f"🎰 {'نتيجة السبين' if lang=='ar' else 'Spin Result'}:\n\n{message}\n\n"
        f"💰 {'رصيدك' if lang=='ar' else 'Balance'}: {updated[1]:.4f} USDT\n"
        f"🎰 {'سبينات متبقية' if lang=='ar' else 'Spins left'}: {updated[0]}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    bot_username = context.bot.username
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    lang = get_lang(user_id, conn)
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
    total_refs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=? AND referral_counted=1", (user_id,))
    counted_refs = c.fetchone()[0]
    conn.close()
    link = f"https://t.me/{bot_username}?start={user_id}"
    if lang == "ar":
        text = (f"👥 الإحالات\n\n🔗 رابطك:\n{link}\n\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 إجمالي الإحالات: {total_refs}\n"
                f"✅ الإحالات المحسوبة: {counted_refs}\n\n"
                f"🎁 سبينة لكل صديق يُكمل 3 مهام!")
        keyboard = [
            [InlineKeyboardButton("🔗 شارك الرابط", switch_inline_query=link)],
            [InlineKeyboardButton("🏠 القائمة", callback_data="menu")],
        ]
    else:
        text = (f"👥 Referrals\n\n🔗 Your Link:\n{link}\n\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 Total Referrals: {total_refs}\n"
                f"✅ Counted Referrals: {counted_refs}\n\n"
                f"🎁 1 spin per friend who completes 3 tasks!")
        keyboard = [
            [InlineKeyboardButton("🔗 Share Link", switch_inline_query=link)],
            [InlineKeyboardButton("🏠 Menu", callback_data="menu")],
        ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    lang = get_lang(user_id, conn)
    conn.close()
    if lang == "ar":
        text = ("📋 المهام المتاحة\n\n"
                "قريباً سيتم إضافة مهام حقيقية!\n\n"
                "كل مهمة = سبينة واحدة 🎰")
        keyboard = [[InlineKeyboardButton("🏠 القائمة", callback_data="menu")]]
    else:
        text = ("📋 Available Tasks\n\n"
                "Real tasks coming soon!\n\n"
                "Each task = 1 Spin 🎰")
        keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    lang = get_lang(user_id, conn)
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row[0] < 2.0:
        await query.edit_message_text(
            f"❌ {'رصيدك' if lang=='ar' else 'Balance'}: {row[0]:.4f} USDT\n\n"
            + ("تحتاج 2 USDT للسحب!\n📋 نفّذ مهام للحصول على سبينات أكثر" if lang=="ar"
               else "You need 2 USDT to withdraw!\n📋 Complete tasks to get more spins"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="profile")]])
        )
        return
    await query.edit_message_text(
        f"💸 {'طلب السحب' if lang=='ar' else 'Withdrawal Request'}\n\n"
        f"{'المبلغ' if lang=='ar' else 'Amount'}: {row[0]:.4f} USDT\n\n"
        + ("أرسل عنوان محفظتك TRC20 للمشرف وسيتم التحويل خلال 24 ساعة 👇" if lang=="ar"
           else "Send your TRC20 wallet address to admin for transfer within 24 hours 👇"),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="profile")]])
    )

async def toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    current = get_lang(user_id, conn)
    new_lang = "en" if current == "ar" else "ar"
    c.execute("UPDATE users SET lang=? WHERE user_id=?", (new_lang, user_id))
    conn.commit()
    conn.close()
    await show_menu(update, context, new_lang)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)

if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(spin_zone, pattern="^spin_zone$"))
    app.add_handler(CallbackQueryHandler(spin, pattern="^spin$"))
    app.add_handler(CallbackQueryHandler(referral, pattern="^referral$"))
    app.add_handler(CallbackQueryHandler(tasks, pattern="^tasks$"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(toggle_lang, pattern="^toggle_lang$"))
    app.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    app.run_polling(drop_pending_updates=True)
