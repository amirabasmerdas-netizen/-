import telebot
from telebot import types
from flask import Flask, request
import json, os

TOKEN = "8275637960:AAHSf_bh-ztbLqtQRVys1KizveKKcEahr8U"
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
        "users": {},              # uid: {name, approved}
        "channels": {},           # uid: channel
        "groups": [],
        "forward_status": {},
        "pending_users": {},
        "pending_channels": {},
        "referrals": {},          # uid: [invited_ids]
        "invited_by": {}          # uid: inviter
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
        kb.add("📨 دعوت دوستان","📊 لاگ من")
        kb.add("📞 ارتباط با ادمین","📘 راهنما")
    if uid == OWNER_ID:
        kb.add("👥 تنظیمات گروه مقصد")
    return kb

# ---------- استارت + رفرال ----------
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name or "نامشخص"
    args = msg.text.split()

    if uid not in db["users"] and uid != OWNER_ID:
        ref = int(args[1]) if len(args)>1 and args[1].isdigit() else None

        db["pending_users"][uid] = name

        if ref and ref != uid and ref in db["users"]:
            db["invited_by"][uid] = ref
            db["referrals"].setdefault(ref, []).append(uid)
            bot.send_message(ref,f"🎉 کاربر جدید با لینک دعوت شما وارد ربات شد\n🆔 {uid}")

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
def approve_user(c):
    action,uid = c.data.split(":")
    uid = int(uid)

    if action=="approve_user":
        db["users"][uid] = db["pending_users"].pop(uid)
        save_db()
        bot.send_message(uid,"✅ درخواست شما تأیید شد\nلطفاً /start بزنید")
        bot.answer_callback_query(c.id,"تأیید شد")
    else:
        db["pending_users"].pop(uid,None)
        save_db()
        bot.send_message(uid,"❌ درخواست شما رد شد")
        bot.answer_callback_query(c.id,"رد شد")

# ---------- دکمه‌ها ----------
@bot.message_handler(func=lambda m: True)
def buttons(msg):
    uid = msg.from_user.id
    t = msg.text

    if uid != OWNER_ID and uid not in db["users"]:
        return

    if t=="📨 دعوت دوستان":
        link=f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid,f"🔗 لینک دعوت شما:\n{link}")

    elif t=="📊 لاگ من":
        invited = db["referrals"].get(uid,[])
        ch = db["channels"].get(str(uid),"ثبت نشده")
        status = "روشن" if db["forward_status"].get(str(uid)) else "خاموش"
        bot.send_message(
            uid,
            f"📊 لاگ شما\n"
            f"📢 کانال: {ch}\n"
            f"▶️ فروارد: {status}\n"
            f"👥 دعوت‌شده‌ها: {len(invited)}\n"
            f"{invited}"
        )

    elif t=="⚙️ تنظیم کانال مبدأ":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("➕ وصل کردن کانال","➖ حذف کانال","⬅️ بازگشت")
        bot.send_message(uid,"پنل تنظیم کانال",reply_markup=kb)

    elif t=="➕ وصل کردن کانال":
        bot.send_message(uid,"@کانال را ارسال کنید")
        bot.register_next_step_handler(msg,add_channel)

    elif t=="➖ حذف کانال":
        bot.send_message(uid,"@کانال را ارسال کنید")
        bot.register_next_step_handler(msg,remove_channel)

    elif t=="▶️ شروع فروارد":
        db["forward_status"][str(uid)] = True
        save_db()
        bot.send_message(uid,"▶️ فروارد فعال شد")

    elif t=="⏹ توقف فروارد":
        db["forward_status"][str(uid)] = False
        save_db()
        bot.send_message(uid,"⏹ فروارد متوقف شد")

    elif t=="👥 تنظیمات گروه مقصد" and uid==OWNER_ID:
        bot.send_message(uid,"@گروه مقصد را ارسال کنید")
        bot.register_next_step_handler(msg,set_group)

    elif t=="⬅️ بازگشت":
        bot.send_message(uid,"بازگشت",reply_markup=main_kb(uid))

# ---------- افزودن کانال + درخواست به مالک ----------
def add_channel(msg):
    uid = msg.chat.id
    ch = msg.text.strip()

    try:
        info = bot.get_chat(ch)
        m = bot.get_chat_member(ch,bot.get_me().id)
        if m.status not in ["administrator","creator"]:
            return bot.send_message(uid,"❌ ربات ادمین کانال نیست")
    except:
        return bot.send_message(uid,"❌ کانال معتبر نیست")

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ پذیرش کانال",callback_data=f"approve_ch:{uid}:{ch}"),
        types.InlineKeyboardButton("❌ رد کانال",callback_data=f"reject_ch:{uid}")
    )

    bot.send_message(
        OWNER_ID,
        f"📢 درخواست کانال\n"
        f"👤 کاربر: {uid}\n"
        f"📛 نام: {info.title}\n"
        f"📝 توضیح: {info.description}\n"
        f"🆔 {info.id}",
        reply_markup=kb
    )

    bot.send_message(uid,"📩 کانال برای بررسی ارسال شد")

# ---------- تأیید کانال توسط مالک ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith(("approve_ch","reject_ch")))
def approve_channel(c):
    data = c.data.split(":")
    action = data[0]

    if action=="approve_ch":
        uid = data[1]
        ch = data[2]
        db["channels"][uid] = ch
        save_db()
        bot.send_message(int(uid),"✅ کانال شما تأیید شد")
        bot.answer_callback_query(c.id,"کانال ثبت شد")
    else:
        uid = data[1]
        bot.send_message(int(uid),"❌ کانال شما رد شد")
        bot.answer_callback_query(c.id,"رد شد")

# ---------- حذف کانال ----------
def remove_channel(msg):
    uid = msg.chat.id
    ch = msg.text.strip()
    if db["channels"].get(str(uid)) == ch:
        del db["channels"][str(uid)]
        save_db()
        bot.send_message(uid,"❌ کانال حذف شد")
    else:
        bot.send_message(uid,"کانالی یافت نشد")

# ---------- تنظیم گروه ----------
def set_group(msg):
    g = msg.text.strip()
    try:
        m = bot.get_chat_member(g,bot.get_me().id)
        if m.status not in ["administrator","creator"]:
            return bot.send_message(msg.chat.id,"❌ ربات ادمین گروه نیست")
        db["groups"].append(g)
        save_db()
        bot.send_message(msg.chat.id,"✅ گروه اضافه شد")
    except:
        bot.send_message(msg.chat.id,"❌ گروه معتبر نیست")

# ---------- فروارد ----------
@bot.channel_post_handler(func=lambda m: True)
def forward(msg):
    chat_id = msg.chat.id
    username = msg.chat.username
    ch_tag = f"@{username}" if username else None

    for uid, ch in db["channels"].items():
        # آیا فروارد برای این کاربر فعاله؟
        if not db["forward_status"].get(uid):
            continue

        # بررسی اینکه پیام از کانال ثبت‌شده اومده
        if ch_tag == ch or str(chat_id) == ch:
            for g in db["groups"]:
                try:
                    bot.forward_message(
                        g,
                        msg.chat.id,
                        msg.message_id
                    )
                except:
                    pass

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
