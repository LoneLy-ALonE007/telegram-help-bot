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

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_TOKEN = "8412647394:AAEDRqeD23Wwm7QqtQZyT7AlygsXUCRHJhU"
bot = telebot.TeleBot(BOT_TOKEN)
tashkent_tz = pytz.timezone("Asia/Tashkent")
now = datetime.now(tashkent_tz)
ADMINS = [6008741577]

# /start komandasi: foydalanuvchini ro'yxatdan o'tkazish
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



def check_and_notify_tasks():
    tashkent_tz = pytz.timezone("Asia/Tashkent")

    while True:
        try:
            with open('tasks.json', 'r') as f:
                tasks = json.load(f)
        except FileNotFoundError:
            tasks = []

        now = datetime.now(tashkent_tz)  # ✅ Toshkent vaqti

        for task in tasks:
            if not task["done"]:
                try:
                    deadline = datetime.strptime(task["deadline"], "%d-%m-%Y")

                    if (deadline - now).days == 1:
                        bot.send_message(
                            task["assigned_to"],
                            f"⚠️ Eslatma: '{task['task']}' vazifasi ertaga ({task['deadline']}) tugaydi."
                        )

                    if now > deadline:
                        bot.send_message(
                            task["assigned_to"],
                            f"⛔ Diqqat! '{task['task']}' vazifasi {task['deadline']} kuni tugagan,\nhali bajarmagansiz!"
                        )

                except Exception as e:
                    print(f"Ogohlantirishda xatolik: {e}")

            # ✅ Har oylik vazifani qayta ishga tushirish
            elif task.get("monthly") and now.day == 1 and task["done"]:
                task["done"] = False
                try:
                    bot.send_message(
                        task["assigned_to"],
                        f"🔄 Har oylik vazifa: '{task['task']}' uchun yangi davr boshlandi.\nIltimos, {task['deadline']} sanasigacha bajaring."
                    )
                except Exception as e:
                    print(f"Har oylik vazifa ogohlantirishida xatolik: {e}")

        with open('tasks.json', 'w') as f:
            json.dump(tasks, f, indent=2)

        time.sleep(3600)
# /bajarilganlar komandasi: admin uchun barcha foydalanuvchilarning bajarilgan vazifalari
@bot.message_handler(commands=['hisobot'])
def show_completed_tasks(message):
    try:
        with open('tasks.json', 'r') as f:
            tasks = json.load(f)
    except FileNotFoundError:
            tasks = []
    completed_tasks = [task for task in tasks if task.get("done")]
    if not completed_tasks:
            bot.send_message(message.chat.id, "✅ Hozircha bajarilgan vazifalar yo'q.")
            return

    last_20 = completed_tasks[-20:]
    report = "📋 <b>Oxirgi 20 ta bajarilgan vazifalar:</b>\n\n"

    for task in last_20:
        if task.get("done"):
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


@bot.message_handler(commands=['vazifalar'])
def show_pending_tasks(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqdan foydalanish huquqi yo‘q.")
        return

    try:
        with open('tasks.json', 'r') as f:
            tasks = json.load(f)
    except FileNotFoundError:
        bot.reply_to(message, "❌ Hali hech qanday vazifa mavjud emas.")
        return

    pending_tasks = [task for task in tasks if not task.get("done", False)]

    if not pending_tasks:
        bot.reply_to(message, "✅ Hamma vazifalar bajarilgan.")
        return

    text = "🔴 Tugallanmagan vazifalar:\n\n"
    for task in pending_tasks[-20:]:  # faqat oxirgi 20 ta
        user_info = bot.get_chat(task["assigned_to"])
        name = user_info.username or f"{user_info.first_name or ''} {user_info.last_name or ''}".strip()
        text += f"❌ {task['task']} - {name} (📅 {task['deadline']})\n"

    bot.send_message(message.chat.id, text)
@bot.message_handler(commands=['vazifa_ochirish'])
def delete_task(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "❌ Sizda bu buyruqdan foydalanish huquqi yo‘q.")
        return

    bot.send_message(message.chat.id, "🗑 O‘chirmoqchi bo‘lgan vazifa nomini to‘liq kiriting:")

    def get_task_name(msg):
        task_name = msg.text.strip()

        try:
            with open('tasks.json', 'r') as f:
                tasks = json.load(f)
        except FileNotFoundError:
            tasks = []

        new_tasks = [task for task in tasks if task["task"] != task_name]

        if len(new_tasks) < len(tasks):
            with open('tasks.json', 'w') as f:
                json.dump(new_tasks, f, indent=2)
            bot.send_message(message.chat.id, f"✅ '{task_name}' vazifasi o‘chirildi.")
        else:
            bot.send_message(message.chat.id, f"❌ '{task_name}' nomli vazifa topilmadi.")

    bot.register_next_step_handler(message, get_task_name)
@bot.message_handler(func=lambda message: message.chat.type in ["group", "supergroup"])
def handle_group_messages(message):
    if message.text.startswith('/start'):
        bot.reply_to(message, "🤖 Bot guruhda ishga tushdi.")


def send_monthly_reminders():
    now = datetime.now(tashkent)
    try:
        with open('monthly_tasks.json', 'r') as f:
            monthly_tasks = json.load(f)
    except FileNotFoundError:
        monthly_tasks = []

    for task in monthly_tasks:
        start_day = task["day_of_month"]
        delta_days = (now.day - start_day)

        # Faqat 5 kun ichida
        if 0 <= delta_days < 5:
            with open('users.json', 'r') as f:
                data = json.load(f)
            for user_id in data["users"]:
                try:
                    bot.send_message(
                        user_id,
                        f"🔔 <b>Doimiy vazifa eslatmasi</b>:\n\n📝 {task['task']}\n🧾 {task['description']}",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"❌ Ogohlantirish yuborishda xatolik: {e}")

        time.sleep(60)

def schedule_jobs():
    schedule.every().day.at("10:00").do(send_monthly_reminders)
    schedule.every().day.at("16:00").do(send_monthly_reminders)

    while True:
        schedule.run_pending()
        time.sleep(60)

@bot.message_handler(commands=['doimiy_vazifa_qoshish'])
def add_monthly_task(message):
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

                try:
                    with open('monthly_tasks.json', 'r') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    data = []

                data.append({
                    "task": task_name,
                    "description": description,
                    "day_of_month": day
                })

                with open('monthly_tasks.json', 'w') as f:
                    json.dump(data, f, indent=2)

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

        try:
            with open('monthly_tasks.json', 'r') as f:
                tasks = json.load(f)
        except FileNotFoundError:
            tasks = []

        new_tasks = [task for task in tasks if task["task"] != task_name]

        if len(new_tasks) < len(tasks):
            with open('monthly_tasks.json', 'w') as f:
                json.dump(new_tasks, f, indent=2)
            bot.send_message(message.chat.id, f"✅ '{task_name}' nomli doimiy vazifa o‘chirildi.")
        else:
            bot.send_message(message.chat.id, f"❌ '{task_name}' nomli doimiy vazifa topilmadi.")

    bot.register_next_step_handler(message, get_task_name)

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


# Thread orqali ishga tushuriladi
threading.Thread(target=schedule_jobs).start()
bot.set_my_commands([
    BotCommand("start", "Botni ishga tushirish"),
    BotCommand("vazifa_berish", "Yangi vazifa yuborish (admin)"),
    BotCommand("doimiy_vazifa_qoshish", "Har oy takrorlanuvchi vazifa qo‘shish"),
    BotCommand("vazifalar", "Tugallanmagan vazifalarni ko‘rish (admin)"),
    BotCommand("hisobot", "Bajarilgan vazifalar (admin)"),
    BotCommand("doimiy_hisobot", "Doimiy vazifalar ro'yxati"),
    BotCommand("vazifa_ochirish", "Vazifani o‘chirish (admin)")
])


# Botni doimiy ishga tushurish
bot.infinity_polling()
