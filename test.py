import telebot
from telebot import types
from flask import Flask, request
import json, os, time

TOKEN = "8341867404:AAG1fmvyiLuHq1HOrr1XdZKmXTVhW1_zBMY"
OWNER_ID = 8321215905
WEBHOOK_URL = "https://3pznnryz17.onrender.com"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DB_FILE = "db.json"

# ---------- دیتابیس ----------
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE,"r") as f:
            return json.load(f)
    return {
        "users": {},
        "channels": {},
        "target_group": None,
        "forward_enabled": False
    }

def save_db():
    with open(DB_FILE,"w") as f:
        json.dump(db,f,indent=4)

db = load_db()

# ---------- سطوح ----------
LEVELS = {
    "normal": {"channels":1,"friends":0},
    "bronze": {"channels":2,"friends":2},
    "silver": {"channels":4,"friends":4},
    "gold": {"channels":10,"friends":10}
}

# ---------- کیبورد ----------
def user_kb(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ افزودن کانال","📨 دعوت دوستان")
    kb.add("📊 وضعیت حساب")
    return kb

def owner_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ روشن کردن فروارد","⛔ خاموش کردن فروارد")
    kb.add("🎯 تنظیم گروه مقصد")
    kb.add("📋 لاگ کاربران")
    return kb

# ---------- استارت ----------
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    ref = msg.text.split(" ")[1] if len(msg.text.split())>1 else None

    if uid not in db["users"]:
        db["users"][uid] = {
            "level":"normal",
            "friends":0,
            "invited_by":ref,
            "approved": False
        }

        if ref and ref.isdigit() and int(ref) in db["users"]:
            inviter = int(ref)
            db["users"][inviter]["friends"] += 1
            bot.send_message(inviter,f"🎉 کاربر جدید با لینک دعوت شما وارد شد!\n👤 {uid}")
            update_level(inviter)

        save_db()

    if uid == OWNER_ID:
        bot.send_message(uid,"👑 پنل مالک",reply_markup=owner_kb())
        return

    if not db["users"][uid]["approved"]:
        bot.send_message(uid,"⏳ درخواست شما ثبت شد، منتظر تایید مالک باشید")
        bot.send_message(OWNER_ID,f"📩 درخواست جدید:\n🆔 {uid}")
        return

    bot.send_message(uid,"👋 خوش آمدید!\nربات آماده استفاده است",reply_markup=user_kb(uid))

# ---------- ارتقای سطح ----------
def update_level(uid):
    f = db["users"][uid]["friends"]
    if f>=10: db["users"][uid]["level"]="gold"
    elif f>=4: db["users"][uid]["level"]="silver"
    elif f>=2: db["users"][uid]["level"]="bronze"
    save_db()

# ---------- دکمه‌ها ----------
@bot.message_handler(func=lambda m: True)
def buttons(msg):
    uid = msg.from_user.id
    t = msg.text

    # مالک
    if uid == OWNER_ID:
        if t=="✅ روشن کردن فروارد":
            db["forward_enabled"]=True
            save_db()
            bot.send_message(uid,"✅ فروارد روشن شد")
        elif t=="⛔ خاموش کردن فروارد":
            db["forward_enabled"]=False
            save_db()
            bot.send_message(uid,"⛔ فروارد خاموش شد")
        elif t=="🎯 تنظیم گروه مقصد":
            bot.send_message(uid,"@گروه مقصد را ارسال کن")
            bot.register_next_step_handler(msg,set_target_group)
        elif t=="📋 لاگ کاربران":
            txt=""
            for u,d in db["users"].items():
                txt+=f"\n🆔 {u} | {d['level']} | دوستان: {d['friends']}"
            bot.send_message(uid,txt or "خالی")
        return

    # کاربر
    if t=="📨 دعوت دوستان":
        link=f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid,f"🔗 لینک دعوت اختصاصی:\n{link}\n👥 دوستان: {db['users'][uid]['friends']}")
    elif t=="📊 وضعیت حساب":
        d=db["users"][uid]
        bot.send_message(uid,f"⭐ سطح: {d['level']}\n👥 دوستان: {d['friends']}")
    elif t=="➕ افزودن کانال":
        bot.send_message(uid,"@کانال را ارسال کن")
        bot.register_next_step_handler(msg,add_channel)

# ---------- تنظیم گروه ----------
def set_target_group(msg):
    g = msg.text.strip()
    try:
        bot.get_chat(g)
        db["target_group"]=g
        save_db()
        bot.send_message(msg.chat.id,"✅ گروه مقصد ثبت شد")
    except:
        bot.send_message(msg.chat.id,"❌ گروه معتبر نیست")

# ---------- افزودن کانال ----------
def add_channel(msg):
    uid=msg.chat.id
    ch=msg.text.strip()
    try:
        member=bot.get_chat_member(ch,bot.get_me().id)
        if member.status not in ["administrator","creator"]:
            return bot.send_message(uid,"❌ ربات باید ادمین کانال باشد")
    except:
        return bot.send_message(uid,"❌ کانال معتبر نیست")

    level=db["users"][uid]["level"]
    limit=LEVELS[level]["channels"]

    user_channels=db["channels"].get(str(uid),[])
    if len(user_channels)>=limit:
        return bot.send_message(uid,"⛔ سقف کانال شما پر شده")

    user_channels.append(ch)
    db["channels"][str(uid)]=user_channels
    save_db()
    bot.send_message(uid,"✅ کانال اضافه شد")

# ---------- فروارد ----------
@bot.channel_post_handler(func=lambda m: True)
def forward(msg):
    if not db["forward_enabled"] or not db["target_group"]:
        return
    for chans in db["channels"].values():
        if msg.chat.username and "@"+msg.chat.username in chans:
            try:
                bot.forward_message(db["target_group"],msg.chat.id,msg.message_id)
            except: pass

# ---------- WEBHOOK ----------
@app.route(f"/{TOKEN}",methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.json)])
    return "OK",200

@app.route("/")
def home():
    return "Bot is running"

if __name__=="__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0",port=10000)
