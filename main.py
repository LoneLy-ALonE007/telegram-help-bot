import telebot
import os
from telebot.types import Message
from datetime import datetime
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
ADMINS = [6008741577]

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
        bot.reply_to(message, "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz.")
    else:
        bot.reply_to(message, "Siz allaqachon ro'yxatdan o'tgansiz.")

@bot.message_handler(commands=['vazifa_berish'])

def send_task_to_users(task_text, deadline):
    with open('users.json', 'r') as f:
        data = json.load(f)

    for user_id in data["users"]:
        try:
            bot.send_message(user_id, f"📝 Yangi vazifa:\n\n{task_text}\n\n🗓 Tugash muddati: {deadline}")
        except Exception as e:
            print(f"❌ Xatolik {user_id} ga yuborishda: {e}")

    tasks.append({
            "task": task_text,
            "deadline": deadline,
            "assigned_to": user_id,
            "done": False
        })

    # Yangi vazifalarni faylga yozish
    with open('tasks.json', 'w') as f:
        json.dump(tasks, f, indent=2)

@bot.message_handler(commands=['vazifa_berish'])
def vazifa_berish(message):
    chat_id = message.chat.id
    markup = types.ForceReply()
    bot.send_message(chat_id, "📝 Vazifa matnini kiriting:", reply_markup=markup)

    @bot.message_handler(func=lambda msg: msg.reply_to_message and msg.reply_to_message.text == "📝 Vazifa matnini kiriting:")
    def qabul_qilish(msg):
        task_text = msg.text
        markup2 = types.ForceReply()
        bot.send_message(chat_id, "🗓 Tugash muddatini kiriting (YYYY-MM-DD HH:MM):", reply_markup=markup2)

        @bot.message_handler(func=lambda m: m.reply_to_message and "Tugash muddatini kiriting" in m.reply_to_message.text)
        def sana_qabul(m):
            deadline = m.text
            # Bu yerga qo‘shamiz:
            send_task_to_users(task_text, deadline)
            bot.send_message(chat_id, "✅ Vazifa yuborildi.")


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
            if (task["task"] == task_name and
                task.get("assigned_to") == user_id and
                not task.get("done", False)):
                task["done"] = True
                updated = True

        if updated:
            with open('tasks.json', 'w') as f:
                json.dump(tasks, f, indent=2)
            bot.send_message(user_id, "✅ Vazifa bajarilgan deb belgilandi.")
        else:
            bot.send_message(user_id, "❌ Bunday vazifa topilmadi yoki allaqachon bajarilgan.")

    bot.register_next_step_handler(message, get_task_name)


bot.polling(non_stop=True)
