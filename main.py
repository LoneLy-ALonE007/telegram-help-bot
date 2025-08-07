import telebot
from telebot import types
import os
import json
import threading
import time
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# /start komandasi: foydalanuvchini ro'yxatdan o'tkazish
@bot.message_handler(commands=['start'])
def register_user(message):
    user_id = message.from_user.id
    try:
        with open('users.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"users": []}

    if user_id not in data["users"]:
        data["users"].append(user_id)
        with open('users.json', 'w') as f:
            json.dump(data, f)
        bot.reply_to(message, "✅ Ro'yxatdan o'tdingiz.")
    else:
        bot.reply_to(message, "Siz allaqachon ro'yxatdan o'tgansiz.")

# Vazifani foydalanuvchilarga yuborish


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


# /vazifa_berish komandasi: admin tomonidan vazifa yuborish
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

# /vazifa_bajarish komandasi: ishchi tomonidan vazifani bajarilgan deb belgilash
@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def handle_done_button(call):
    user_id = call.from_user.id
    task_name = call.data[5:]  # "done_" dan keyingi qism

    try:
        with open('tasks.json', 'r') as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

    updated = False
    for task in tasks:
        if (task["task"] == task_name and task["assigned_to"] == user_id and not task["done"]):
            task["done"] = True
            updated = True

    if updated:
        with open('tasks.json', 'w') as f:
            json.dump(tasks, f, indent=2)
        bot.answer_callback_query(call.id, "✅ Vazifa bajarildi deb belgilandi.")
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    else:
        bot.answer_callback_query(call.id, "❌ Vazifa topilmadi yoki allaqachon bajarilgan.")

@bot.message_handler(commands=['vazifa_bajarish'])
def bajarildi(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "📝 Qaysi vazifani bajardingiz? (aniq matnini yozing)")

    def get_task_name(msg):
        task_name = msg.text.strip()

        try:
            with open('tasks.json', 'r') as f:
                tasks = json.load(f)
        except FileNotFoundError:
            tasks = []

        updated = False
        for task in tasks:
            if (task["task"] == task_name and task.get("assigned_to") == user_id and not task.get("done", False)):
                task["done"] = True
                updated = True

        if updated:
            with open('tasks.json', 'w') as f:
                json.dump(tasks, f, indent=2)
            bot.send_message(user_id, "✅ Vazifa bajarilgan deb belgilandi.")
        else:
            bot.send_message(user_id, "❌ Bunday vazifa topilmadi yoki allaqachon bajarilgan.")

    bot.register_next_step_handler(message, get_task_name)

def check_and_notify_tasks():
    while True:
        try:
            with open('tasks.json', 'r') as f:
                tasks = json.load(f)
        except FileNotFoundError:
            tasks = []

        now = datetime.now()

        for task in tasks:
            if not task["done"]:
                try:
                    deadline = datetime.strptime(task["deadline"], "%d-%m-%Y")

                    # 1 kun qolganda eslatma
                    if (deadline - now).days == 1:
                        bot.send_message(
                            task["assigned_to"],
                            f"⚠️ Eslatma: '{task['task']}' vazifasi ertaga ({task['deadline']}) tugaydi."
                        )

                    # Muddat o‘tib ketgan bo‘lsa — har 1 soatda ogohlantirish
                    if now > deadline:
                        bot.send_message(
                            task["assigned_to"],
                            f"⛔ Diqqat! '{task['task']}' vazifasi {task['deadline']} kuni tugagan,\nhali bajarmagansiz!"
                        )
                except Exception as e:
                    print(f"Ogohlantirishda xatolik: {e}")

        time.sleep(3600)  # 1 soatda bir marta ishga tushadi

# Botni doimiy ishga tushurish
bot.infinity_polling()

