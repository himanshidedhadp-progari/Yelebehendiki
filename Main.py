import sqlite3
import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION (Yahan apni details daalein)
# ═══════════════════════════════════════════════════════════════════
BOT_TOKEN = "9266856284:AAFl8st2YynqQ8LtTHQOwTl6E_zuz0Wq5vw"  # BotFather se token daalein
OWNER_ID = 6244053739               # Aapki Telegram ID (Get from @userinfobot)
API_BASE_URL = "https://mayank-vehicle-num-5defe6.rivendeploy.com"

DB_FILE = "api_keys.db"

# ═══════════════════════════════════════════════════════════════════
# DATABASE SETUP
# ═══════════════════════════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_string TEXT UNIQUE,
            client_name TEXT,
            status TEXT DEFAULT 'active',
            expiry_date TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_key(key, name, days):
    expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    created = datetime.datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO keys (key_string, client_name, expiry_date, created_at) VALUES (?, ?, ?, ?)",
                  (key, name, expiry, created))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_all_keys():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key_string, client_name, status, expiry_date FROM keys ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def revoke_key(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE keys SET status='revoked' WHERE key_string=?", (key,))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0

def revive_key(key, days):
    new_expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE keys SET status='active', expiry_date=? WHERE key_string=?", (new_expiry, key))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0

# ═══════════════════════════════════════════════════════════════════
# TELEGRAM BOT COMMANDS
# ═══════════════════════════════════════════════════════════════════
def is_owner(uid):
    return uid == OWNER_ID

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🚫 Yeh bot sirf Owner ke liye hai.")
        return
    
    text = (
        "👑 *Welcome Boss!*\n\n"
        "API Keys manage karne ke liye niche diye gaye commands use karein:\n\n"
        "🔹 /newkey `<key>` `<days>` `<name>` - Nayi key banayein\n"
        "🔹 /mykeys - Saari keys dekhein\n"
        "🔹 /revoke `<key>` - Key ko band karein\n"
        "🔹 /revive `<key>` `<days>` - Purani key wapas chalu karein\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def new_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    
    if len(ctx.args) < 3:
        await update.message.reply_text("Usage: `/newkey <custom_key> <days> <name>`\nExample: `/newkey VIP-RAHUL 30 Rahul`", parse_mode="Markdown")
        return

    custom_key = ctx.args[0]
    try:
        days = int(ctx.args[1])
        name = " ".join(ctx.args[2:])
    except ValueError:
        await update.message.reply_text("❌ Days ek number hona chahiye.")
        return

    if add_key(custom_key, name, days):
        expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        api_link = f"{API_BASE_URL}/?key={custom_key}&search=MH02DZ4323"
        
        text = (
            f"✅ *Key Successfully Created!*\n\n"
            f"👤 Client: {name}\n"
            f"🔑 Key: `{custom_key}`\n"
            f"📅 Expires: {expiry}\n"
            f"⏱️ Valid for: {days} days\n\n"
            f"🔗 *API Link:*\n`{api_link}`\n\n"
            f"_(Isko copy karke client ko bhej dein)_"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Yeh key pehle se exist karti hai. Koi aur naam try karein.")

async def my_keys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    
    keys = get_all_keys()
    if not keys:
        await update.message.reply_text("📭 Abhi tak koi key nahi banayi gayi.")
        return

    text = "🔑 *Aapki API Keys*\n━━━━━━━━━━━━━━━━━━\n\n"
    for k in keys:
        status_icon = "🟢" if k[2] == "active" else "🔴"
        text += f"{status_icon} *{k[1]}*\n"
        text += f"Key: `{k[0]}`\n"
        text += f"Status: {k[2].upper()} | Expiry: {k[3]}\n\n"

    if len(text) > 4000:
        text = text[:4000] + "\n... (aur keys hain)"
        
    await update.message.reply_text(text, parse_mode="Markdown")

async def revoke(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not ctx.args:
        await update.message.reply_text("Usage: `/revoke <key>`", parse_mode="Markdown")
        return
        
    key = ctx.args[0]
    if revoke_key(key):
        await update.message.reply_text(f"🚫 Key `{key}` revoke kar di gayi hai.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Key nahi mili.")

async def revive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: `/revive <key> <days>`\nExample: `/revive VIP-RAHUL 30`", parse_mode="Markdown")
        return
        
    key = ctx.args[0]
    try:
        days = int(ctx.args[1])
    except ValueError:
        await update.message.reply_text("❌ Days ek number hona chahiye.")
        return
        
    if revive_key(key, days):
        expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        await update.message.reply_text(f"✅ Key `{key}` wapas chalu ho gayi!\nNayi Expiry: {expiry}", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Key nahi mili.")

# ═══════════════════════════════════════════════════════════════════
# RUN BOT
# ═══════════════════════════════════════════════════════════════════
def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newkey", new_key))
    app.add_handler(CommandHandler("mykeys", my_keys))
    app.add_handler(CommandHandler("revoke", revoke))
    app.add_handler(CommandHandler("revive", revive))
    
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
