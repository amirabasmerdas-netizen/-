import telebot
from telebot import types
from flask import Flask, request
import json, os

TOKEN = "8341867404:AAG1fmvyiLuHq1HOrr1XdZKmXTVhW1_zBMY"
OWNER_ID = 8321215905
WEBHOOK_URL = "https://3pznnryz17.onrender.com"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DB_FILE = "db.json"

# ---------- دیتابیس ----------
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {},
        "channels": {},
        "pending_users": {},
        "pending_channels": {},
        "groups": [],
        "forward_status": {}
    }

def save_db():
    with open(DB_FILE,"w",encoding="utf-8") as f:
        json.dump(db,f,indent=4,ensure_ascii=False)

db = load_db()

# ---------- کیبورد ----------
def main_kb(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⚙️ تنظیم کانال مبدأ")
    kb.add("📋 لیست")
    kb.add("▶️ شروع فروارد","⏹ توقف فروارد")
    if uid != OWNER_ID:
        kb.add("📞 ارتباط با ادمین","📘 راهنما")
    if uid == OWNER_ID:
        kb.add("👥 تنظیمات گروه مقصد")
    return kb

# ---------- استارت ----------
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name

    if uid not in db["users"] and uid != OWNER_ID:
        db["pending_users"][uid] = name
        save_db()

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ پذیرش",callback_data=f"approve_user:{uid}"),
            types.InlineKeyboardButton("❌ رد",callback_data=f"reject_user:{uid}")
        )

        bot.send_message(
            OWNER_ID,
            f"📩 درخواست عضویت\n👤 نام: {name}\n🆔 آیدی عددی: {uid}",
            reply_markup=kb
        )

        bot.send_message(uid,"⏳ درخواست شما برای مالک ارسال شد")
        return

    if uid in db["users"] or uid == OWNER_ID:
        bot.send_message(uid,"✅ خوش آمدید",reply_markup=main_kb(uid))

# ---------- تأیید کاربر ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith(("approve_user","reject_user")))
def user_approve(c):
    action,uid = c.data.split(":")
    uid = int(uid)

    if action=="approve_user":
        db["users"][uid] = db["pending_users"].pop(uid)
        save_db()
        bot.send_message(uid,"✅ درخواست شما تأیید شد\nلطفاً دوباره /start بزنید")
        bot.answer_callback_query(c.id,"کاربر اضافه شد")
    else:
        db["pending_users"].pop(uid,None)
        save_db()
        bot.send_message(uid,"❌ متأسفانه درخواست شما رد شد")
        bot.answer_callback_query(c.id,"رد شد")

# ---------- دکمه‌ها ----------
@bot.message_handler(func=lambda m: True)
def buttons(msg):
    uid = msg.from_user.id
    t = msg.text

    if uid != OWNER_ID and uid not in db["users"]:
        return

    if t=="⚙️ تنظیم کانال مبدأ":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("➕ وصل کردن کانال","➖ حذف کانال","⬅️ بازگشت")
        bot.send_message(uid,"پنل تنظیم کانال",reply_markup=kb)

    elif t=="➕ وصل کردن کانال":
        bot.send_message(uid,"@کانال را ارسال کنید")
        bot.register_next_step_handler(msg,add_channel)

    elif t=="➖ حذف کانال":
        bot.send_message(uid,"@کانال برای حذف")
        bot.register_next_step_handler(msg,remove_channel)

    elif t=="▶️ شروع فروارد":
        db["forward_status"][str(uid)] = True
        save_db()
        bot.send_message(uid,"▶️ فروارد برای شما روشن شد")

    elif t=="⏹ توقف فروارد":
        db["forward_status"][str(uid)] = False
        save_db()
        bot.send_message(uid,"⏹ فروارد برای شما متوقف شد")

    elif t=="📋 لیست":
        if uid==OWNER_ID:
            txt="📋 لیست کامل:\n"
            for u,ch in db["channels"].items():
                txt+=f"\n👤 {u} → {ch}"
            txt+=f"\n\n👥 گروه‌ها:\n" + "\n".join(db["groups"])
            bot.send_message(uid,txt or "خالی")
        else:
            ch=db["channels"].get(str(uid))
            bot.send_message(uid,f"📋 کانال شما:\n{ch if ch else 'ثبت نشده'}")

    elif t=="📞 ارتباط با ادمین":
        bot.send_message(uid,f"📞 ارتباط با ادمین:\n@your_username")

    elif t=="📘 راهنما":
        bot.send_message(uid,"📘 ابتدا ربات را ادمین کانال کنید سپس لینک @کانال را ارسال نمایید")

    elif t=="👥 تنظیمات گروه مقصد" and uid==OWNER_ID:
        bot.send_message(uid,"@گروه مقصد را ارسال کنید")
        bot.register_next_step_handler(msg,set_group)

    elif t=="⬅️ بازگشت":
        bot.send_message(uid,"بازگشت به پنل اصلی",reply_markup=main_kb(uid))

# ---------- افزودن کانال ----------
def add_channel(msg):
    uid = msg.chat.id
    ch = msg.text.strip()

    if not ch.startswith("@"):
        return bot.send_message(uid,"❌ لینک باید با @ باشد")

    try:
        m = bot.get_chat_member(ch,bot.get_me().id)
        if m.status not in ["administrator","creator"]:
            return bot.send_message(uid,"❌ ربات ادمین کانال نیست")
        info = bot.get_chat(ch)
    except:
        return bot.send_message(uid,"❌ کانال معتبر نیست")

    db["pending_channels"][uid] = ch
    save_db()

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ تأیید",callback_data=f"confirm_ch:{uid}"),
        types.InlineKeyboardButton("❌ رد",callback_data=f"cancel_ch:{uid}")
    )

    bot.send_message(
        uid,
        f"نام: {info.title}\nبیو: {info.description}\nID: {info.id}",
        reply_markup=kb
    )

# ---------- تأیید کانال ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith(("confirm_ch","cancel_ch")))
def channel_confirm(c):
    action,uid = c.data.split(":")
    uid=int(uid)

    if action=="confirm_ch":
        ch = db["pending_channels"].pop(uid)
        db["channels"][str(uid)] = ch
        save_db()
        bot.send_message(uid,"📩 کانال شما برای بررسی به مالک ارسال شد")
        bot.send_message(OWNER_ID,f"📩 درخواست کانال:\n👤 {uid}\n📢 {ch}")
    else:
        db["pending_channels"].pop(uid,None)
        save_db()
        bot.send_message(uid,"❌ عملیات لغو شد")

# ---------- حذف کانال ----------
def remove_channel(msg):
    uid=msg.chat.id
    ch=msg.text.strip()
    if db["channels"].get(str(uid))==ch:
        del db["channels"][str(uid)]
        save_db()
        bot.send_message(uid,"❌ کانال حذف شد")
    else:
        bot.send_message(uid,"کانالی یافت نشد")

# ---------- تنظیم گروه ----------
def set_group(msg):
    g=msg.text.strip()
    try:
        m=bot.get_chat_member(g,bot.get_me().id)
        if m.status not in ["administrator","creator"]:
            return bot.send_message(msg.chat.id,"❌ ربات ادمین گروه نیست")
        db["groups"].append(g)
        save_db()
        bot.send_message(msg.chat.id,"✅ گروه مقصد اضافه شد")
    except:
        bot.send_message(msg.chat.id,"❌ گروه معتبر نیست")

# ---------- فروارد ----------
@bot.channel_post_handler(func=lambda m: True)
def forward(msg):
    for uid,ch in db["channels"].items():
        if db["forward_status"].get(uid):
            if msg.chat.username and "@"+msg.chat.username==ch:
                for g in db["groups"]:
                    try:
                        bot.forward_message(g,msg.chat.id,msg.message_id)
                    except: pass

# ---------- WEBHOOK ----------
@app.route(f"/{TOKEN}",methods=["POST"])
def webhook():
    bot.process_new_updates([types.Update.de_json(request.json)])
    return "OK",200

@app.route("/")
def home():
    return "Bot is running"

if __name__=="__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0",port=10000)
