import telebot
import os
from telebot.types import Message
from datetime import datetime

ADMINS = [6008741577]
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Assalomu alaykum! Men ishchi vazifalar botiman.")



tasks = {}  # {'user_id': [{'nom': ..., 'tavsif': ..., 'deadline': ...}, ...]}
user_states = {}  # user_id: qaysi bosqichda
temp_task_data = {}  # user_id: {'nom': ..., 'tavsif': ...}


@bot.message_handler(commands=['vazifa_berish'])
def vazifa_berish(message: Message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "Sizga bu amalni bajarishga ruxsat yo‘q.")
        return
    user_states[message.from_user.id] = 'kirit_nom'
    bot.reply_to(message, "✅ Vazifa nomini kiriting:")


@bot.message_handler(func=lambda msg: msg.from_user.id in user_states)
def process_task_steps(message: Message):
    user_id = message.from_user.id
    state = user_states[user_id]

    if state == 'kirit_nom':
        temp_task_data[user_id] = {'nom': message.text}
        user_states[user_id] = 'kirit_tavsif'
        bot.send_message(user_id, "✏️ Vazifa tavsifini kiriting:")

    elif state == 'kirit_tavsif':
        temp_task_data[user_id]['tavsif'] = message.text
        user_states[user_id] = 'kirit_start'
        bot.send_message(user_id, "🕒 Vazifa boshlanish vaqtini kiriting (YYYY-MM-DD HH:MM):")

    elif state == 'kirit_start':
        try:
            start_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
            temp_task_data[user_id]['start_time'] = start_time
            user_states[user_id] = 'kirit_deadline'
            bot.send_message(user_id, "📅 Vazifa tugash muddatini kiriting (YYYY-MM-DD HH:MM):")
        except ValueError:
            bot.send_message(user_id, "❗ Noto‘g‘ri format. Iltimos, YYYY-MM-DD HH:MM formatda yozing.")

    elif state == 'kirit_deadline':
        try:
            deadline = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
            start_time = temp_task_data[user_id]['start_time']
            if deadline <= start_time:
                bot.send_message(user_id, "❗ Tugash muddati boshlanish vaqtidan keyin bo‘lishi kerak.")
                return

            temp_task_data[user_id]['deadline'] = deadline

            # Saqlash
            task = temp_task_data[user_id]
            tasks.setdefault(user_id, []).append(task)

            bot.send_message(user_id, f"✅ Vazifa saqlandi:\n"
                                      f"📌 {task['nom']}\n"
                                      f"📋 {task['tavsif']}\n"
                                      f"🟢 Boshlanish: {task['start_time']}\n"
                                      f"⏰ Tugash: {task['deadline']}")

            # Tozalash
            user_states.pop(user_id)
            temp_task_data.pop(user_id)

        except ValueError:
            bot.send_message(user_id, "❗ Noto‘g‘ri format. Iltimos, YYYY-MM-DD HH:MM formatda yozing.")


bot.polling(non_stop=True)
