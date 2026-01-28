import telebot, json, os
from telebot import types
from flask import Flask, request
from datetime import date

# ---------- CONFIG ----------
TOKEN = "8341867404:AAG1fmvyiLuHq1HOrr1XdZKmXTVhW1_zBMY"
OWNER_ID = 8321215905
USE_WEBHOOK = True
WEBHOOK_URL = "https://3pznnryz17.onrender.com"
DB_FILE = "db.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ---------- LEVELS ----------
LEVELS = {
    "normal": {"channels":1, "limit":1000},
    "bronze": {"channels":2, "limit":2000},
    "silver": {"channels":4, "limit":4000},
    "gold":   {"channels":10,"limit":10000},
}

# ---------- DB ----------
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE,"r") as f:
            return json.load(f)
    return {
        "owners":[OWNER_ID],
        "allowed_users":[],
        "pending_users":[],
        "forward_on":False,
        "target_group":None,
        "users":{}
    }

def save_db():
    with open(DB_FILE,"w") as f:
        json.dump(db,f,indent=4)

db = load_db()

# ---------- USER INIT ----------
def init_user(uid):
    uid=str(uid)
    if uid not in db["users"]:
        db["users"][uid]={
            "level":"normal",
            "channels":[],
            "daily":{},
            "referrals":0
        }
        save_db()

# ---------- KEYBOARDS ----------
def main_kb(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if uid in db["allowed_users"] or uid in db["owners"]:
        kb.add("▶️ شروع فوروارد","⏹ توقف فوروارد")
        kb.add("➕ افزودن کانال","➖ حذف کانال")
        kb.add("👥 دعوت دوستان","📊 آمار من")
    else:
        kb.add("🔐 درخواست دسترسی")
    if uid in db["owners"]:
        kb.add("🎯 تنظیم گروه مقصد","📋 لاگ کاربران")
    return kb

def owner_req_kb(uid):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ تأیید",callback_data=f"ok_{uid}"),
        types.InlineKeyboardButton("❌ رد",callback_data=f"no_{uid}")
    )
    return kb

# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(m):
    uid=m.from_user.id
    init_user(uid)

    # referral
    if len(m.text.split())>1 and m.text.split()[1].startswith("ref_"):
        ref=m.text.split()[1].split("_")[1]
        if ref!=str(uid) and ref in db["users"]:
            db["users"][ref]["referrals"]+=1
            bot.send_message(int(ref),
                f"👤 {m.from_user.first_name} با لینک دعوت شما وارد ربات شد 🎉")
            r=db["users"][ref]["referrals"]
            if r>=10: db["users"][ref]["level"]="gold"
            elif r>=4: db["users"][ref]["level"]="silver"
            elif r>=2: db["users"][ref]["level"]="bronze"
            save_db()

    bot.send_message(uid,"🤖 خوش اومدی",reply_markup=main_kb(uid))

# ---------- ACCESS ----------
@bot.message_handler(func=lambda m:m.text=="🔐 درخواست دسترسی")
def req(m):
    uid=m.from_user.id
    if uid in db["allowed_users"]:
        return bot.send_message(uid,"✅ قبلاً تأیید شدی")
    if uid in db["pending_users"]:
        return bot.send_message(uid,"⏳ درخواستت در حال بررسیه")

    db["pending_users"].append(uid)
    save_db()
    bot.send_message(
        OWNER_ID,
        f"📩 درخواست دسترسی\n👤 {m.from_user.first_name}\n🆔 {uid}",
        reply_markup=owner_req_kb(uid)
    )
    bot.send_message(uid,"📨 درخواست ارسال شد")

@bot.callback_query_handler(func=lambda c:c.data.startswith(("ok_","no_")))
def decide(c):
    uid=int(c.data.split("_")[1])
    if c.data.startswith("ok_"):
        db["allowed_users"].append(uid)
        bot.send_message(uid,
            "🎉 خوش آمدید!\n✅ دسترسی شما فعال شد\n🔁 لطفاً /start را دوباره بزنید")
    else:
        bot.send_message(uid,"❌ درخواست رد شد")
    if uid in db["pending_users"]:
        db["pending_users"].remove(uid)
    save_db()
    bot.answer_callback_query(c.id,"انجام شد")

# ---------- OWNER ----------
@bot.message_handler(func=lambda m:m.text=="🎯 تنظیم گروه مقصد")
def set_group_step(m):
    if m.from_user.id not in db["owners"]: return
    bot.send_message(m.chat.id,"@group ؟")
    bot.register_next_step_handler(m,set_group)

def set_group(m):
    db["target_group"]=m.text.strip()
    save_db()
    bot.send_message(m.chat.id,"✅ گروه مقصد تنظیم شد")

@bot.message_handler(func=lambda m:m.text=="📋 لاگ کاربران")
def logs(m):
    if m.from_user.id not in db["owners"]: return
    text="📊 لاگ کاربران:\n\n"
    for uid,u in db["users"].items():
        text+=(
            f"🆔 {uid}\n"
            f"🎚 سطح: {u['level']}\n"
            f"📣 دعوت: {u['referrals']}\n"
            f"📡 کانال‌ها: {len(u['channels'])}\n\n"
        )
    bot.send_message(m.chat.id,text)

# ---------- STATS ----------
@bot.message_handler(func=lambda m:m.text=="📊 آمار من")
def stats(m):
    u=db["users"][str(m.from_user.id)]
    bot.send_message(
        m.chat.id,
        f"🎚 سطح: {u['level']}\n"
        f"👥 دعوت‌ها: {u['referrals']}\n"
        f"📡 کانال‌ها: {len(u['channels'])}"
    )

# ---------- CHANNEL ----------
@bot.message_handler(func=lambda m:m.text=="➕ افزودن کانال")
def add_ch_step(m):
    bot.send_message(m.chat.id,"@channel ؟")
    bot.register_next_step_handler(m,add_channel)

def add_channel(m):
    uid=str(m.chat.id)
    ch=m.text.strip()
    user=db["users"][uid]
    lvl=LEVELS[user["level"]]

    if len(user["channels"])>=lvl["channels"]:
        return bot.send_message(m.chat.id,"❌ سقف کانال پر شده")

    try:
        member=bot.get_chat_member(ch,bot.get_me().id)
        if member.status not in ["administrator","creator"]:
            return bot.send_message(m.chat.id,"❌ ربات ادمین نیست")
    except:
        return bot.send_message(m.chat.id,"❌ کانال نامعتبر")

    user["channels"].append(ch)
    save_db()
    bot.send_message(m.chat.id,"✅ کانال اضافه شد")

@bot.message_handler(func=lambda m:m.text=="➖ حذف کانال")
def rm_ch_step(m):
    bot.send_message(m.chat.id,"@channel ؟")
    bot.register_next_step_handler(m,rm_channel)

def rm_channel(m):
    uid=str(m.chat.id)
    ch=m.text.strip()
    if ch in db["users"][uid]["channels"]:
        db["users"][uid]["channels"].remove(ch)
        save_db()
        bot.send_message(m.chat.id,"❌ حذف شد")

# ---------- LIMIT ----------
def can_forward(uid):
    today=str(date.today())
    user=db["users"][str(uid)]
    lvl=LEVELS[user["level"]]

    user["daily"].setdefault(today,0)
    if user["daily"][today]>=lvl["limit"]:
        return False
    user["daily"][today]+=1
    save_db()
    return True

# ---------- FORWARD ----------
@bot.channel_post_handler(func=lambda m:True)
def forward(m):
    if not db["forward_on"] or not db["target_group"]: return
    for uid,data in db["users"].items():
        if can_forward(uid):
            try:
                bot.forward_message(db["target_group"],m.chat.id,m.message_id)
            except:
                pass

# ---------- CONTROL ----------
@bot.message_handler(func=lambda m:m.text=="▶️ شروع فوروارد")
def start_fw(m):
    if m.from_user.id not in db["allowed_users"]+db["owners"]: return
    db["forward_on"]=True
    save_db()
    bot.send_message(m.chat.id,"▶️ فوروارد فعال شد")

@bot.message_handler(func=lambda m:m.text=="⏹ توقف فوروارد")
def stop_fw(m):
    if m.from_user.id not in db["allowed_users"]+db["owners"]: return
    db["forward_on"]=False
    save_db()
    bot.send_message(m.chat.id,"⏹ فوروارد متوقف شد")

# ---------- WEBHOOK ----------
@app.route("/",methods=["GET"])
def home():
    return "alive"

@app.route(f"/{TOKEN}",methods=["POST"])
def hook():
    bot.process_new_updates([telebot.types.Update.de_json(request.json)])
    return "ok"

def run():
    if USE_WEBHOOK:
        bot.remove_webhook()
        bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
        app.run(host="0.0.0.0",port=10000)
    else:
        bot.infinity_polling()

run()
