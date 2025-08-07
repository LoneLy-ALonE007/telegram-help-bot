import telebot
from telebot import types
import os

from datetime import datetime
import json


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

def send_task_to_users(task_text, description, start_time, deadline):
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
            bot.send_message(
                user_id,
                f"📝 Yangi vazifa:\n\n<b>{task_text}</b>\n\n🧾 {description}\n\n📆 Boshlanish: {start_time}\n⏰ Tugash: {deadline}",
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"❌ {user_id} ga yuborishda xatolik: {e}")

        tasks.append({
            "task": task_text,
            "description": description,
            "start": start_time,
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
    bot.send_message(chat_id, "📝 Vazifa matnini kiriting:")

    def get_task(msg):
        task_text = msg.text
        bot.send_message(chat_id, "🗓 Tugash muddatini kiriting (YYYY-MM-DD HH:MM):")

        def get_deadline(deadline_msg):
            deadline = deadline_msg.text
            send_task_to_users(task_text, deadline)
            bot.send_message(chat_id, "✅ Vazifa yuborildi.")

        bot.register_next_step_handler(deadline_msg := msg, get_deadline)

    bot.register_next_step_handler(message, get_task)

# /vazifa_bajarish komandasi: ishchi tomonidan vazifani bajarilgan deb belgilash
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


# Botni doimiy ishga tushurish
bot.infinity_polling()

