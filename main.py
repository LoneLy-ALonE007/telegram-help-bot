import telebot
from telebot import types
import os
import json
import threading
import time
from datetime import datetime
import pytz
import schedule
from telebot.types import BotCommand
from flask import Flask, request

# =================== Sozlamalar ===================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8412647394:AAEDRqeD23Wwm7QqtQZyT7AlygsXUCRHJhU")
WEBHOOK_HOST = "https://sening-bot-adresing.onrender.com"  # Render yoki Railway domeni
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = telebot.TeleBot(BOT_TOKEN)
tashkent_tz = pytz.timezone("Asia/Tashkent")
ADMINS = [6008741577]

app = Flask(__name__)

# =================== Foydalanuvchi ro'yxatga olish ===================
@bot.message_handler(commands=['start'])
def register_user(message):
    chat_id = message.chat.id
    try:
        with open('users.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"users": []}

    if chat_id not in data["users"]:
        data["users"].append(chat_id)
        with open('users.json', 'w') as f:
            json.dump(data, f)
        bot.send_message(chat_id, "✅ Ro'yxatdan o'tdingiz.")
    else:
        bot.send_message(chat_id, "Siz allaqachon ro'yxatdan o'tgansiz.")

# =================== Vazifani foydalanuvchilarga yuborish ===================
def send_task_to_users(task_text, description, start_date, deadline):
    try:
        with open('users.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"users": []}

    try:
        with open('tasks.json', 'r') as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

    for user_id in data["users"]:
        try:
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton("✅ Vazifa bajarildi", callback_data=f"done_{task_text}")
            markup.add(btn)

            bot.send_message(
                user_id,
                f"📝 Yangi vazifa:\n\n<b>{task_text}</b>\n\n🧾 {description}\n\n📆 Boshlanish: {start_date}\n⏰ Tugash: {deadline}",
                parse_mode='HTML',
                reply_markup=markup
            )
        except Exception as e:
            print(f"❌ {user_id} ga yuborishda xatolik: {e}")

        tasks.append({
            "task": task_text,
            "description": description,
            "start": start_date,
            "deadline": deadline,
            "assigned_to": user_id,
            "done": False
        })

    with open('tasks.json', 'w') as f:
        json.dump(tasks, f, indent=2)

# =================== Adminni ogohlantirish ===================
def notify_admins(task_name, user_id):
    try:
        user = bot.get_chat(user_id)
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = f"@{user.username}" if user.username else "(username yo'q)"
    except Exception as e:
        full_name = "Ism topilmadi"
        username = "(username yo'q)"
        print(f"Foydalanuvchini olishda xatolik: {e}")

    for admin_id in ADMINS:
        try:
            bot.send_message(
                admin_id,
                f"ℹ️ Foydalanuvchi: <b>{full_name}</b>\nUsername: <code>{username}</code>\n\n✅ Vazifa: <b>{task_name}</b> bajarildi.",
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"Adminni ogohlantirishda xatolik: {e}")

# =================== Vazifa berish (admin) ===================
@bot.message_handler(commands=['vazifa_berish'])
def vazifa_berish(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📝 Vazifa nomini kiriting:")

    def get_task_name(msg):
        task_text = msg.text
        bot.send_message(chat_id, "🧾 Vazifa tavsifini kiriting:")

        def get_description(msg2):
            description = msg2.text
            bot.send_message(chat_id, "📆 Boshlanish sanasini kiriting (DD-MM-YYYY):")

            def get_start_date(msg3):
                start_date = msg3.text
                bot.send_message(chat_id, "⏰ Tugash sanasini kiriting (DD-MM-YYYY):")

                def get_deadline(msg4):
                    deadline = msg4.text
                    send_task_to_users(task_text, description, start_date, deadline)
                    bot.send_message(chat_id, "✅ Vazifa barcha ishchilarga yuborildi.")

                bot.register_next_step_handler(msg3, get_deadline)

            bot.register_next_step_handler(msg2, get_start_date)

        bot.register_next_step_handler(msg, get_description)

    bot.register_next_step_handler(message, get_task_name)

# =================== Vazifa bajarildi tugmasi ===================
@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def handle_done_button(call):
    user_id = call.from_user.id
    task_name = call.data[5:]

    try:
        with open('tasks.json', 'r') as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

    updated = False
    for task in tasks:
        if task["task"] == task_name and task["assigned_to"] == user_id and not task["done"]:
            task["done"] = True
            updated = True

    if updated:
        with open('tasks.json', 'w') as f:
            json.dump(tasks, f, indent=2)
        notify_admins(task_name, user_id)
        bot.answer_callback_query(call.id, "✅ Vazifa bajarildi deb belgilandi.")
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    else:
        bot.answer_callback_query(call.id, "❌ Vazifa topilmadi yoki allaqachon bajarilgan.")

# =================== Doimiy eslatmalar ===================
def send_monthly_reminders():
    now = datetime.now(tashkent_tz)
    try:
        with open('monthly_tasks.json', 'r') as f:
            monthly_tasks = json.load(f)
    except FileNotFoundError:
        monthly_tasks = []

    for task in monthly_tasks:
        start_day = task["day_of_month"]
        delta_days = (now.day - start_day)
        if 0 <= delta_days < 5:
            try:
                with open('users.json', 'r') as f:
                    data = json.load(f)
                for user_id in data["users"]:
                    bot.send_message(
                        user_id,
                        f"🔔 <b>Doimiy vazifa eslatmasi</b>:\n\n📝 {task['task']}\n🧾 {task['description']}",
                        parse_mode='HTML'
                    )
            except Exception as e:
                print(f"❌ Ogohlantirish yuborishda xatolik: {e}")

def schedule_jobs():
    schedule.every().day.at("10:00").do(send_monthly_reminders)
    schedule.every().day.at("16:00").do(send_monthly_reminders)
    while True:
        schedule.run_pending()
        time.sleep(60)

# =================== Webhook marshrutlari ===================
@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

@app.route("/", methods=['GET'])
def index():
    return "Bot ishlayapti!", 200

# =================== Botni ishga tushurish ===================
if __name__ == "__main__":
    threading.Thread(target=schedule_jobs).start()
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
