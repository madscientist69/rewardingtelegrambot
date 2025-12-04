import os
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from utils import load_db, save_db

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = WEBHOOK_DOMAIN + WEBHOOK_PATH

app = FastAPI()
bot = Bot(BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

# ------------------------
#  LOAD DATABASE
# ------------------------
db = load_db()

def ensure_user(uid):
    if uid not in db["users"]:
        db["users"][uid] = {
            "points": 0,
            "rewards": [],
            "history": [],
            "setup_rewards": False
        }
        save_db(db)

# ------------------------
#  COMMANDS
# ------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)

    await update.message.reply_text(
        "👋 Selamat datang di Reward Bot!\n\n"
        "Gunakan /help untuk melihat semua fitur."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📘 *Panduan Reward Bot*\n\n"
        "/start - Mulai bot & inisiasi akun\n"
        "/help - Menampilkan panduan\n"
        "/setrewards - Buat daftar reward Anda\n"
        "/rewards - Lihat daftar reward\n"
        "/points - Lihat poin\n"
        "/add <tugas> <poin> - Tambah poin dari tugas\n"
        "/redeem <nomor> - Tukar poin dengan reward\n"
        "/history - Lihat riwayat aktivitas\n\n"
        "Format /setrewards:\n"
        "3 Snack kecil\n"
        "9 BingXue\n"
        "18 Ebook\n"
    )
    await update.message.reply_markdown(text)


async def setrewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)

    db["users"][uid]["setup_rewards"] = True
    save_db(db)

    await update.message.reply_text(
        "Silakan kirim _list reward_ Anda dalam satu pesan.\n"
        "Format tiap baris:\n"
        "<poin> <nama reward>\n\n"
        "Contoh:\n"
        "3 Snack kecil\n"
        "9 BingXue\n"
        "18 Ebook"
    )


async def rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)

    rewards = db["users"][uid]["rewards"]
    if not rewards:
        await update.message.reply_text("❌ Anda belum membuat reward. Gunakan /setrewards.")
        return

    text = "🎁 *Reward Anda:*\n\n"
    for i, r in enumerate(rewards, start=1):
        text += f"{i}. {r['points']} poin → {r['name']}\n"

    await update.message.reply_markdown(text)


async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)

    pts = db["users"][uid]["points"]
    await update.message.reply_text(f"💰 Poin Anda: {pts}")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)

    if len(context.args) < 2:
        await update.message.reply_text("Format: /add <nama tugas> <poin>")
        return

    *task, pts = context.args
    task = " ".join(task)

    try:
        pts = int(pts)
    except:
        await update.message.reply_text("Poin harus angka.")
        return

    user = db["users"][uid]
    user["points"] += pts
    user["history"].append(f"+{pts} poin dari tugas: {task}")

    save_db(db)

    await update.message.reply_text(
        f"✔️ '{task}' ditambahkan. Poin +{pts}.\n"
        f"Total poin: {user['points']}"
    )


async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)

    user = db["users"][uid]

    if len(context.args) != 1:
        await update.message.reply_text("Format: /redeem <nomor>")
        return

    try:
        idx = int(context.args[0]) - 1
    except:
        await update.message.reply_text("Nomor reward tidak valid.")
        return

    if idx < 0 or idx >= len(user["rewards"]):
        await update.message.reply_text("Nomor reward tidak ada.")
        return

    reward = user["rewards"][idx]

    if user["points"] < reward["points"]:
        await update.message.reply_text("❌ Poin tidak cukup.")
        return

    user["points"] -= reward["points"]
    user["history"].append(f"-{reward['points']} poin untuk reward: {reward['name']}")
    save_db(db)

    await update.message.reply_text(
        f"🎉 Anda berhasil redeem:\n{reward['name']} (−{reward['points']} poin)\n"
        f"Poin tersisa: {user['points']}"
    )


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)

    hist = db["users"][uid]["history"]
    if not hist:
        await update.message.reply_text("📜 Belum ada riwayat.")
        return

    text = "📜 *Riwayat Anda:*\n\n"
    for h in hist:
        text += f"- {h}\n"

    await update.message.reply_markdown(text)


# ------------------------
# TEXT HANDLER (SETREWARDS)
# ------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)

    user = db["users"][uid]

    if not user["setup_rewards"]:
        return

    lines = update.message.text.strip().split("\n")
    new_rewards = []

    for line in lines:
        parts = line.split(" ", 1)
        if len(parts) != 2:
            await update.message.reply_text("Format salah di salah satu baris.")
            return

        try:
            pts = int(parts[0])
        except:
            await update.message.reply_text("Poin harus angka di setiap baris.")
            return

        new_rewards.append({"points": pts, "name": parts[1]})

    user["rewards"] = new_rewards
    user["setup_rewards"] = False
    save_db(db)

    await update.message.reply_text("✔️ Reward berhasil disimpan!")


# ------------------------
# REGISTER HANDLERS
# ------------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_cmd))
application.add_handler(CommandHandler("setrewards", setrewards))
application.add_handler(CommandHandler("rewards", rewards))
application.add_handler(CommandHandler("points", points))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("redeem", redeem))
application.add_handler(CommandHandler("history", history))

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))


# ------------------------
# WEBHOOK FASTAPI
# ------------------------
@app.on_event("startup")
async def startup():
    await bot.initialize()
    await application.initialize()
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook set:", WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}
