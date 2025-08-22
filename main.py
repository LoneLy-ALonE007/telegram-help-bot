import telebot
from telebot import types
import os
import json
import threading
import time
import pytz
import schedule
from telebot.types import BotCommand
from datetime import datetime
from collections import defaultdict

# Bot tokenini o'qish (avvalgi qatorda to'g'ri belgilang!)
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8412647394:AAEDRqeD23Wwm7QqtQZyT7AlygsXUCRHJhU"
bot = telebot.TeleBot(BOT_TOKEN)

tashkent_tz = pytz.timezone("Asia/Tashkent")
ADMINS = [6008741577]

bot.remove_webhook()




def run_with_timezone():
    now = datetime.now(tashkent_tz).strftime("%H:%M")
    if now in ["10:00", "16:00"]:
        send_monthly_reminders()


def schedule_jobs():
    while True:
        run_with_timezone()
        time.sleep(60)
# --- FOYDALANUVCHILAR RO'YXATI --- #
def load_users():
    try:
        with open('users.json', 'r') as f:
            data = json.load(f)
            return data.get("users", [])
    except FileNotFoundError:
        return []

def save_users(users):
    with open('users.json', 'w') as f:
        json.dump({"users": users}, f, indent=2)

# --- VAZIFALAR --- #
def load_tasks():
    try:
        with open('tasks.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_tasks(tasks):
    with open('tasks.json', 'w') as f:
        json.dump(tasks, f, indent=2)

# --- FOYDALANUVCHI RO'YXATIGA QO'SHISH (/start) --- #
@bot.message_handler(commands=['start'])
def register_user(message):
    chat_id = message.chat.id
    users = load_users()

    if chat_id not in users:
        users.append(chat_id)
        save_users(users)
        bot.send_message(chat_id, "✅ Ro'yxatdan o'tdingiz.")
    else:
        bot.send_message(chat_id, "Siz allaqachon ro'yxatdan o'tgansiz.")

# --- VAZIFA YUBORISH (ADMIN) --- #
@bot.message_handler(commands=['vazifa_berish'])
def vazifa_berish(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqni ishlatish huquqi yo'q.")
        return

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

                    # Vazifani foydalanuvchilarga yuborish
                    send_task_to_users(task_text, description, start_date, deadline)
                    bot.send_message(chat_id, "✅ Vazifa barcha ishchilarga yuborildi.")

                bot.register_next_step_handler(msg3, get_deadline)

            bot.register_next_step_handler(msg2, get_start_date)

        bot.register_next_step_handler(msg, get_description)

    bot.register_next_step_handler(message, get_task_name)

def send_task_to_users(task_text, description, start_date, deadline):
    users = load_users()
    tasks = load_tasks()

    for user_id in users:
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

    save_tasks(tasks)

# --- VAZIFA BAJARILGANINI BELGILASH (Callback) --- #
@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def handle_done_button(call):
    user_id = call.from_user.id
    task_name = call.data[5:]

    tasks = load_tasks()
    updated = False

    for task in tasks:
        if task["task"] == task_name and not task["done"]:
            task["done"] = True
            updated = True

    if updated:
        save_tasks(tasks)
        notify_admins(task_name, user_id)
        bot.answer_callback_query(call.id, "✅ Vazifa bajarildi deb belgilandi.")
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    else:
        bot.answer_callback_query(call.id, "❌ Vazifa topilmadi yoki allaqachon bajarilgan.")

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

# --- BAJARILGAN VAZIFALAR HISOBOTI (admin) --- #
@bot.message_handler(commands=['hisobot'])
def show_completed_tasks(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqni ishlatish huquqi yo'q.")
        return

    tasks = load_tasks()
    completed_tasks = [task for task in tasks if task.get("done")]
    if not completed_tasks:
        bot.send_message(message.chat.id, "✅ Hozircha bajarilgan vazifalar yo'q.")
        return

    last_20 = completed_tasks[-20:]
    report = "📋 <b>Oxirgi 20 ta bajarilgan vazifalar:</b>\n\n"

    for task in last_20:
        user_id = task["assigned_to"]
        try:
            user = bot.get_chat(user_id)
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            username = f"@{user.username}" if user.username else "(username yo'q)"
        except Exception as e:
            full_name = "Ism topilmadi"
            username = "(username yo'q)"
            print(f"Foydalanuvchini olishda xatolik: {e}")

        report += f"✅ <b>{task['task']}</b>\n👤 {full_name} {username}\n\n"

    bot.send_message(message.chat.id, report, parse_mode='HTML')

# --- TUGALLANMAGAN VAZIFALAR (admin) --- #
@bot.message_handler(commands=['vazifalar'])
def show_pending_tasks(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqni ishlatish huquqi yo'q.")
        return

    tasks = load_tasks()
    pending_tasks = [task for task in tasks if not task.get("done", False)]

    if not pending_tasks:
        bot.reply_to(message, "✅ Hamma vazifalar bajarilgan.")
        return

    text = "🔴 Tugallanmagan vazifalar:\n\n"
    for task in pending_tasks[-20:]:
        try:
            user_info = bot.get_chat(task["assigned_to"])
            name = user_info.username or f"{user_info.first_name or ''} {user_info.last_name or ''}".strip()
        except Exception as e:
            name = "(foydalanuvchi ma'lumot topilmadi)"
            print(f"Foydalanuvchini olishda xatolik: {e}")

        text += f"❌ {task['task']} - {name} (📅 {task['deadline']})\n"

    bot.send_message(message.chat.id, text)

# --- VAZIFANI O'CHIRISH (admin) --- #
@bot.message_handler(commands=['vazifa_ochirish'])
def delete_task(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqni ishlatish huquqi yo'q.")
        return

    bot.send_message(message.chat.id, "🗑 O‘chirmoqchi bo‘lgan vazifa nomini to‘liq kiriting:")

    def get_task_name(msg):
        task_name = msg.text.strip()
        tasks = load_tasks()

        new_tasks = [task for task in tasks if task["task"] != task_name]

        if len(new_tasks) < len(tasks):
            save_tasks(new_tasks)
            bot.send_message(message.chat.id, f"✅ '{task_name}' vazifasi o‘chirildi.")
        else:
            bot.send_message(message.chat.id, f"❌ '{task_name}' nomli vazifa topilmadi.")

    bot.register_next_step_handler(message, get_task_name)

# --- DOIMIY VAZIFALAR (HAR OY) --- #
def load_monthly_tasks():
    try:
        with open('monthly_tasks.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_monthly_tasks(tasks):
    with open('monthly_tasks.json', 'w') as f:
        json.dump(tasks, f, indent=2)

# ➕ Doimiy vazifa qo‘shish
@bot.message_handler(commands=['doimiy_vazifa_qoshish'])
def add_monthly_task(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqni ishlatish huquqi yo'q.")
        return

    chat_id = message.chat.id
    bot.send_message(chat_id, "📝 Doimiy vazifa nomini kiriting:")

    def get_name(msg):
        task_name = msg.text
        bot.send_message(chat_id, "🧾 Vazifa tavsifini kiriting:")

        def get_desc(msg2):
            description = msg2.text
            bot.send_message(chat_id, "📆 Har oy nechinchi sanada boshlansin? (1-28)")

            def get_day(msg3):
                try:
                    day = int(msg3.text)
                    if day < 1 or day > 28:
                        raise ValueError()
                except ValueError:
                    bot.send_message(chat_id, "❌ Xato: 1 dan 28 gacha son kiriting.")
                    return

                tasks = load_monthly_tasks()
                tasks.append({
                    "task": task_name,
                    "description": description,
                    "day_of_month": day
                })
                save_monthly_tasks(tasks)

                bot.send_message(chat_id, "✅ Doimiy vazifa qo‘shildi.")

            bot.register_next_step_handler(msg2, get_day)

        bot.register_next_step_handler(msg, get_desc)

    bot.register_next_step_handler(message, get_name)

@bot.message_handler(commands=['doimiy_vazifa_ochirish'])
def delete_monthly_task(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqdan foydalanish huquqi yo‘q.")
        return

    bot.send_message(message.chat.id, "🗑 O‘chirmoqchi bo‘lgan doimiy vazifa nomini to‘liq kiriting:")

    def get_task_name(msg):
        task_name = msg.text.strip()

        tasks = load_monthly_tasks()
        new_tasks = [task for task in tasks if task["task"] != task_name]

        if len(new_tasks) < len(tasks):
            save_monthly_tasks(new_tasks)
            bot.send_message(message.chat.id, f"✅ '{task_name}' nomli doimiy vazifa o‘chirildi.")
        else:
            bot.send_message(message.chat.id, f"❌ '{task_name}' nomli doimiy vazifa topilmadi.")

    bot.register_next_step_handler(message, get_task_name)

def send_monthly_reminders():
    now = datetime.now(tashkent_tz)
    monthly_tasks = load_monthly_tasks()

    for task in monthly_tasks:
        start_day = task["day_of_month"]
        delta_days = now.day - start_day

        # ✅ faqat 5 kun ichida va hali bajarilmagan bo‘lsa
        if 0 <= delta_days < 5 and not task.get("done", False):
            try:
                with open('users.json', 'r') as f:
                    users = json.load(f)["users"]
            except FileNotFoundError:
                users = []

            for user_id in users:
                try:
                    markup = types.InlineKeyboardMarkup()
                    btn = types.InlineKeyboardButton("✅ Doimiy vazifa bajarildi", callback_data=f"monthly_done_{task['task']}")
                    markup.add(btn)

                    bot.send_message(
                        user_id,
                        f"🔔 <b>Doimiy vazifa</b>:\n\n📝 {task['task']}\n🧾 {task['description']}",
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                except Exception as e:
                    print(f"❌ Ogohlantirish yuborishda xatolik: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("monthly_done_"))
def handle_monthly_done(call):
    user_id = call.from_user.id
    task_name = call.data.replace("monthly_done_", "")

    tasks = load_monthly_tasks()
    updated = False

    for task in tasks:
        if task["task"] == task_name and not task.get("done", False):
            task["done"] = True
            updated = True

            # ✅ Adminlarga xabar
            try:
                user = bot.get_chat(user_id)
                full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                username = f"@{user.username}" if user.username else "(username yo'q)"

                for admin_id in ADMINS:
                    bot.send_message(
                        admin_id,
                        f"ℹ️ Foydalanuvchi: <b>{full_name}</b> {username}\n✅ Doimiy vazifa: <b>{task_name}</b> bajarildi.",
                        parse_mode="HTML"
                    )
            except Exception as e:
                print(f"Admin ogohlantirishda xatolik: {e}")

    if updated:
        save_monthly_tasks(tasks)
        bot.answer_callback_query(call.id, "✅ Vazifa bajarildi deb belgilandi.")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    else:
        bot.answer_callback_query(call.id, "❌ Bu vazifa allaqachon bajarilgan.")

def reset_monthly_tasks():
    now = datetime.now(tashkent_tz)
    tasks = load_monthly_tasks()
    updated = False

    if now.day == 1:  # har oyning 1-kuni
        for task in tasks:
            if task.get("done", False):
                task["done"] = False
                updated = True

    if updated:
        save_monthly_tasks(tasks)
        print("♻️ Doimiy vazifalar qayta faollashtirildi.")

def schedule_jobs():
    schedule.every().day.at("5:00").do(send_monthly_reminders)
    schedule.every().day.at("11:00").do(send_monthly_reminders)

    schedule.every().day.at("00:05").do(reset_monthly_tasks)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Thread orqali ishga tushuriladi
threading.Thread(target=schedule_jobs, daemon=True).start()

@bot.message_handler(commands=['doimiy_hisobot'])
def show_monthly_tasks(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqdan foydalanish huquqi yo‘q.")
        return

    try:
        with open('monthly_tasks.json', 'r') as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

    if not tasks:
        bot.send_message(message.chat.id, "ℹ️ Hozircha hech qanday doimiy vazifa mavjud emas.")
        return

    text = "📋 <b>Doimiy vazifalar ro‘yxati:</b>\n\n"
    for i, task in enumerate(tasks, start=1):
        text += f"{i}. 📝 <b>{task['task']}</b>\n"
        text += f"   🧾 {task['description']}\n"
        text += f"   📆 Har oy {task['day_of_month']}-sana\n\n"

    bot.send_message(message.chat.id, text, parse_mode='HTML')


attendance = defaultdict(lambda: defaultdict(dict))


def keldim(update, context):
    user_id = update.message.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    attendance[user_id][today]['keldim'] = time_now
    update.message.reply_text(f"Siz {today} kuni soat {time_now} da keldingiz.")


def kettim(update, context):
    user_id = update.message.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M:%S")

    if 'keldim' not in attendance[user_id][today]:
        update.message.reply_text("Siz hali keldingiz deb yozmadingiz!")
        return

    attendance[user_id][today]['kettim'] = time_now
    update.message.reply_text(f"Siz {today} kuni soat {time_now} da ketdingiz.")


def hisobot(update, context):
    user_id = update.message.from_user.id
    user_data = attendance[user_id]

    # Hisobot uchun oy va yil kerak bo'ladi (masalan: 2025-08)
    from_date = datetime.now().strftime("%Y-%m")

    kunlar = []
    for date in user_data:
        if date.startswith(from_date):
            if 'keldim' in user_data[date]:
                kunlar.append(date)

    update.message.reply_text(f"Siz bu oyda {len(kunlar)} kun keldingiz.")

# Botni doimiy ishga tushurish
bot.infinity_polling()
