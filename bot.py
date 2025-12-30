import os
import sqlite3
import asyncio
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ChatJoinRequestHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5422522348

PROMO_PLANS = {
    "1000": ("₹499", 1000),
    "5000": ("₹1999", 5000),
    "10000": ("₹3499", 10000),
}

PAYMENT_UPI = ""
PROMO_IMAGE = "https://i.imgur.com/5KXJ7Qp.jpg"

logging.basicConfig(level=logging.INFO)

# ---------------- DATABASE ----------------
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    content TEXT,
    photo_id TEXT,
    limit_users INTEGER
)
""")
db.commit()


def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    db.commit()


def remove_user(user_id):
    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    db.commit()


# ---------------- /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)

    await update.message.reply_text(
        "👋 Hello!\n\n"
        "This bot sends promotional messages automatically.\n\n"
        "We have 100k+ Users of data & of all Category\n\n"
        "For Paid Promotion: /promote\n"
        "jjj"
    )


# ---------------- /promote ----------------
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1000 Users – ₹499", callback_data="plan_1000")],
        [InlineKeyboardButton("5000 Users – ₹1999", callback_data="plan_5000")],
        [InlineKeyboardButton("10000 Users – ₹3499", callback_data="plan_10000")],
    ]

    await update.message.reply_text(
        "📢 *PAID PROMOTION DETAILS*\n\n"
        "💼 Service: Channel Promotion\n\n"
        "💳 Payment Method (UPI)\n"
        f"• `{PAYMENT_UPI}`\n\n"
        "📌 Instructions\n"
        "1️⃣ Choose a plan\n"
        "2️⃣ Complete the payment\n"
        "3️⃣ Send payment screenshot\n\n"
        "⏱️ Approval Time: 1–24 hours",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

# ---------------- JOIN REQUEST (ONLY DM PROMO) ----------------
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    save_user(user.id)

    image_url = "https://cricchamp.in/wp-content/uploads/2023/05/Screenshot-2023-05-18-at-7.54.33-AM.png"  # ✅ valid image URL

    caption = "🔥 *BEST PREDICTIONS CHANNELS* 🔥👇\n\n"

    keyboard = [
        [InlineKeyboardButton("🏏 CRICKET PREDICTION 🏏", url="https://t.me/+PQTY4_vhTco5Zjll")],
        [InlineKeyboardButton("👑 SESSION KING 👑", url="https://t.me/+_7pgMhyDe8AzYzU1")],
        [InlineKeyboardButton("💥 IPL MATCH FIXER 💥", url="https://t.me/+RGnQfgoIbAI4NTc1")],
        [InlineKeyboardButton("❤️ IPL KA BAAP ❤️", url="https://t.me/+Sh9erckTGbcxM2Q1")],
        [InlineKeyboardButton("🎉 TODAY WINNER 🎉", url="https://t.me/+k4kHAoV4JyU2ODVl")],
        [InlineKeyboardButton("👑 CRICKET ANALYST 👑", url="https://t.me/+S5HM3-_fOrRmMTk1")],
        [InlineKeyboardButton("💜 BEST TIPPER 💜", url="https://t.me/+wiSCnKP7yQk5ZDc1")],
    ]

    try:
        await context.bot.send_photo(
            chat_id=user.id,
            photo=image_url,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
    except TelegramError:
        pass



# ---------------- CALLBACKS (FINAL FIX) ----------------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # ====================================================
    # 1️⃣ USER PROMOTION PLAN (EVERYONE)
    # ====================================================
    if data.startswith("plan_"):
        plan_key = data.split("_")[1]

        if plan_key not in PROMO_PLANS:
            await query.message.reply_text("❌ Invalid plan")
            return

        price, limit_users = PROMO_PLANS[plan_key]

        context.user_data.clear()
        context.user_data["plan_users"] = limit_users
        context.user_data["awaiting_payment"] = True

        await query.message.reply_text(
            f"✅ *Plan Selected*\n\n"
            f"👥 Users: {limit_users}\n"
            f"💰 Price: {price}\n\n"
            "📸 Please send your *payment screenshot* now.",
            parse_mode="Markdown",
        )
        return

    # ====================================================
    # 🚫 BELOW THIS → ADMIN ONLY
    # ====================================================
    if user_id != ADMIN_ID:
        await query.answer("❌ Admin only", show_alert=True)
        return

    # ====================================================
    # 2️⃣ ADMIN PANEL
    # ====================================================
    if data == "admin_count":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        await query.message.reply_text(f"👥 Total Users: {total}")
        return

    if data == "admin_broadcast":
        context.application.bot_data["broadcast"] = True
        await query.message.reply_text("📢 Send broadcast message now.")
        return

    # ====================================================
    # 3️⃣ ADMIN PROMO APPROVAL
    # ====================================================
    if data.startswith("approve_"):
        promo_id = int(data.split("_")[1])

        cursor.execute(
            "SELECT content, limit_users FROM promotions WHERE id=?",
            (promo_id,),
        )
        row = cursor.fetchone()
        if not row:
            await query.message.reply_text("❌ Promotion not found")
            return

        content, limit_users = row

        cursor.execute("SELECT user_id FROM users LIMIT ?", (limit_users,))
        users = cursor.fetchall()

        sent = removed = 0
                for (uid,) in users:
            try:
                await context.bot.send_message(uid, content)
                sent += 1
                await asyncio.sleep(0.1)

            except TelegramError as e:
                error_text = str(e).lower()

                # ONLY remove user if bot is blocked or chat is invalid
                if "blocked" in error_text or "chat not found" in error_text:
                    remove_user(uid)
                    removed += 1

                # DO NOT remove for temporary errors
                continue



        cursor.execute("DELETE FROM promotions WHERE id=?", (promo_id,))
        db.commit()

        await query.message.edit_caption(
            f"✅ Promotion Approved\n📤 Sent: {sent}\n🚮 Removed: {removed}"
        )
        return

    if data.startswith("reject_"):
        promo_id = int(data.split("_")[1])
        cursor.execute("DELETE FROM promotions WHERE id=?", (promo_id,))
        db.commit()
        await query.message.edit_caption("❌ Promotion Rejected")
        return

# ---------------- RECEIVE USER DATA ----------------
async def receive(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # ✅ SAFETY GUARD
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    # ---------- ADMIN BROADCAST ----------
    if user_id == ADMIN_ID and context.application.bot_data.get("broadcast"):
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = removed = 0
        for (uid,) in users:
            try:
                await update.message.copy(chat_id=uid)
                sent += 1
                await asyncio.sleep(0.1)
            except TelegramError as e:
    error_text = str(e).lower()

    if "blocked" in error_text or "chat not found" in error_text:
        remove_user(uid)
        removed += 1

    continue


        context.application.bot_data["broadcast"] = False
        await update.message.reply_text(
            f"✅ Broadcast Done\n📤 Sent: {sent}\n🚮 Removed: {removed}"
        )
        return

    # ---------- PAYMENT SCREENSHOT ----------
    if context.user_data.get("awaiting_payment") and update.message.photo:
        context.user_data["payment_photo"] = update.message.photo[-1].file_id
        context.user_data["awaiting_payment"] = False
        context.user_data["awaiting_ad"] = True

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=context.user_data["payment_photo"],
            caption=f"💰 Payment Screenshot\nUser ID: {user_id}",
        )

        await update.message.reply_text(
            "✅ Payment screenshot received.\n\n"
            "📩 Now send your *ad message*."
        )
        return

    # ---------- AD MESSAGE ----------
    if context.user_data.get("awaiting_ad") and update.message.text:
        ad_text = update.message.text
        plan_users = context.user_data.get("plan_users")

        cursor.execute(
            "INSERT INTO promotions (user_id, content, limit_users) VALUES (?, ?, ?)",
            (user_id, ad_text, plan_users),
        )
        db.commit()
        promo_id = cursor.lastrowid

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=context.user_data.get("payment_photo"),
            caption=(
                "🆕 *New Promotion Request*\n\n"
                f"👤 User ID: `{user_id}`\n"
                f"👥 Users: {plan_users}\n\n"
                f"📝 *Ad Message:*\n{ad_text}"
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{promo_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{promo_id}")
                ]
            ]),
            parse_mode="Markdown",
        )

        context.user_data.clear()

        await update.message.reply_text(
            "⏳ Your promotion is under review.\n"
            "You will be notified after admin approval."
        )
        return


# ---------------- ADMIN PANEL ----------------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Total Users", callback_data="admin_count")],
    ]

    await update.message.reply_text(
        "🛠 *Admin Panel*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.ALL, receive))

    print("🤖 Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()





