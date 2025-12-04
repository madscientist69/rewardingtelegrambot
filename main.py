import os
import json
import urllib.parse
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# -------------------- CONFIG ENV --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN")

if not BOT_TOKEN:
    raise Exception("ENV BOT_TOKEN missing")
if not WEBHOOK_DOMAIN:
    raise Exception("ENV WEBHOOK_DOMAIN missing")

ENCODED_TOKEN = urllib.parse.quote(BOT_TOKEN, safe="")
WEBHOOK_PATH = f"/webhook/{ENCODED_TOKEN}"
WEBHOOK_URL = WEBHOOK_DOMAIN + WEBHOOK_PATH

# -------------------- FASTAPI ------------------------
app = FastAPI()
bot = Bot(BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()

DB_FILE = "db.json"

# -------------------- DATABASE UTILS --------------------
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            f.write("{}")
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# -------------------- COMMANDS --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    db = load_db()

    if str(user.id) not in db:
        db[str(user.id)] = {
            "points": 0,
            "rewards": [],
            "history": []
        }
        save_db(db)

    await update.message.reply_text(
        "Selamat datang!\n"
        "Silakan kirim daftar reward menggunakan /setrewards.\n"
        "Format:\n"
        "reward - poin\n"
        "contoh:\n"
        "Snack kecil - 3\n"
        "BingXue - 9\n"
        "Buku - 18"
    )


async def setrewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    db = load_db()

    await update.message.reply_text(
        "Kirim daftar reward kamu.\n"
        "Setiap baris = reward baru.\n"
        "Format: Nama reward - poin"
    )

    context.user_data["awaiting_rewards"] = True


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    db = load_db()

    # Jika menunggu reward list
    if context.user_data.get("awaiting_rewards"):
        lines = text.strip().split("\n")
        rewards = []

        for line in lines:
            if "-" not in line:
                continue
            name, pts = line.split("-", 1)
            rewards.append({
                "name": name.strip(),
                "points": int(pts.strip())
            })

        db[str(user.id)]["rewards"] = rewards
        save_db(db)

        context.user_data["awaiting_rewards"] = False

        return await update.message.reply_text("Reward list berhasil disimpan!")


async def rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    db = load_db()

    user_data = db.get(str(user.id))
    if not user_data or not user_data["rewards"]:
        return await update.message.reply_text("Reward list kosong. Gunakan /setrewards")

    msg = "🎁 *Reward kamu:*\n"
    for i, r in enumerate(user_data["rewards"], start=1):
        msg += f"{i}. {r['name']} — {r['points']} poin\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    db = load_db()
    pts = db[str(user.id)]["points"]
    await update.message.reply_text(f"💰 Poin kamu: *{pts}*", parse_mode="Markdown")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    db = load_db()

    if len(context.args) < 2:
        return await update.message.reply_text("Format: /add <nama tugas> <poin>")

    task_name = " ".join(context.args[:-1])
    pts = int(context.args[-1])

    db[str(user.id)]["points"] += pts
    db[str(user.id)]["history"].append(
        f"Selesai: {task_name} (+{pts})"
    )
    save_db(db)

    await update.message.reply_text(f"✔ Ditambahkan!\nTugas: {task_name}\nPoin: {pts}")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    db = load_db()

    hist = db[str(user.id)]["history"]
    if not hist:
        return await update.message.reply_text("History kosong.")

    msg = "📜 *History:*\n"
    for h in hist:
        msg += f"- {h}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    db = load_db()

    if len(context.args) != 1:
        return await update.message.reply_text("Format: /redeem <nomor reward>")

    idx = int(context.args[0]) - 1
    user_data = db[str(user.id)]
    rewards = user_data["rewards"]

    if idx < 0 or idx >= len(rewards):
        return await update.message.reply_text("Reward tidak ditemukan.")

    reward = rewards[idx]

    if user_data["points"] < reward["points"]:
        return await update.message.reply_text("Poin tidak cukup.")

    user_data["points"] -= reward["points"]
    user_data["history"].append(f"Redeem: {reward['name']} (-{reward['points']})")

    save_db(db)

    await update.message.reply_text(
        f"🎉 Kamu mendapatkan reward:\n*{reward['name']}*",
        parse_mode="Markdown"
    )


async def helpcmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - mulai\n"
        "/setrewards - isi daftar reward\n"
        "/rewards - lihat reward\n"
        "/points - lihat poin\n"
        "/add <tugas> <poin> - tambah poin\n"
        "/history - riwayat\n"
        "/redeem <no> - tukarkan reward\n"
    )

# -------------------- REGISTER HANDLERS --------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("setrewards", setrewards))
application.add_handler(CommandHandler("rewards", rewards))
application.add_handler(CommandHandler("points", points))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("history", history))
application.add_handler(CommandHandler("redeem", redeem))
application.add_handler(CommandHandler("help", helpcmd))

application.add_handler(CommandHandler("setrewards", setrewards))
application.add_handler(CommandHandler("history", history))
application.add_handler(CommandHandler("help", helpcmd))

application.add_handler(CommandHandler("help", helpcmd))
application.add_handler(CommandHandler("history", history))

# Handler untuk menangkap text biasa
from telegram.ext import MessageHandler, filters
application.add_handler(MessageHandler(filters.TEXT, message_handler))


# -------------------- STARTUP - SET WEBHOOK --------------------
@app.on_event("startup")
async def startup():
    await bot.initialize()
    await application.initialize()
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook aktif di:", WEBHOOK_URL)


# -------------------- WEBHOOK RECEIVER --------------------
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}
