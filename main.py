import os
import http.server
import threading
import telebot
from telebot import types


# --- НАСТРОЙКИ ---
API_TOKEN = "8691191999:AAF7Cvci600khCulIk976e7-gzgG0oRMl4E"
ADMIN_ID = 1099402750
PORT = int(os.environ.get("PORT", "10000"))

bot = telebot.TeleBot(API_TOKEN)
user_data = {}


# --- ВСПОМОГАТЕЛЬНЫЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ---
class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


def start_http_server():
    try:
        httpd = http.server.HTTPServer(("0.0.0.0", PORT), SilentHandler)
        print(f"Вспомогательный веб-сервер запущен на порту {PORT}...")
        httpd.serve_forever()
    except Exception as e:
        print(f"Критическая ошибка веб-сервера: {e}")


# --- КЛАВИАТУРЫ ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton("⚠️ Сообщить о проблеме"),
        types.KeyboardButton("ℹ️ Справочная информация"),
    )
    return markup


def get_info_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 Документы при приеме на работу", callback_data="info_docs"),
        types.InlineKeyboardButton("🤝 Обязанности нанимателя при приеме", callback_data="info_boss"),
        types.InlineKeyboardButton("🎓 Распределение и пенсионный стаж", callback_data="info_pension"),
        types.InlineKeyboardButton("🚫 Кому не ставится испытательный срок", callback_data="info_test"),
        types.InlineKeyboardButton("🤒 Расчет больничного для новичков", callback_data="info_sick"),
        types.InlineKeyboardButton("❓ ТОП Вопросов молодых специалистов", callback_data="info_faq"),
    )
    return markup


def get_back_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Вернуться в меню", callback_data="info_back_to_menu"))
    return markup


# --- КОМАНДА СТАРТ ---
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    user_id = message.from_user.id
    user_data.pop(user_id, None)

    welcome_text = (
        "👋 Здравствуйте! Данный бот создан для сбора и оперативного решения "
        "проблемных вопросов молодых специалистов Наровлянского района.\n\n"
        "Вы можете отправить обращение (текст + фото) или ознакомиться со "
        "справочной информацией о ваших правах, выплатах и гарантиях."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu())


# --- СПРАВОЧНИК ---
@bot.message_handler(func=lambda message: message.text == "ℹ️ Справочная информация")
def send_info_menu(message):
    bot.send_message(
        message.chat.id,
        "📚 *Памятка молодого специалиста*\n\nВыберите интересующую вас тему:",
        reply_markup=get_info_menu(),
        parse_mode="Markdown",
    )


INFO_PAGES = {
    "docs": "📋 *Какие документы нужно предъявить нанимателю?*\n\n✔️ Паспорт / ID-карта\n✔️ Документы воинского учета\n✔️ Диплом\n✔️ Свидетельство о направлении\n✔️ Медсправка",
    "boss": "🤝 *Обязанности нанимателя:*\n\n✔️ Заключить договор\n✔️ Оформить приказ\n✔️ Ознакомить с обязанностями под подпись\n✔️ Провести инструктаж по охране труда",
    "pension": "🎓 *Стаж:*\n\n✅ Время учебы дневной — общий стаж.\n✅ Отработка — страховой стаж (идут взносы ФСЗН).",
    "test": "🚫 *Испытательный срок не ставится:*\n\n▪️ Молодым специалистам после ВУЗов/СУЗов\n▪️ Лицам до 18 лет\n▪️ При переводе к другому нанимателю",
    "sick": "🤒 *Больничный с 1 июля 2024:*\n\nМинимум привязан к МЗП (726 руб). За полный месяц болезни — 100% от МЗП.",
    "faq": "❓ *Вопросы:*\n\n1. Выходить 1 августа.\n2. Декрет и армия входят в срок отработки.\n3. По собственному желанию уволиться нельзя.",
}


@bot.callback_query_handler(func=lambda call: call.data.startswith("info_"))
def handle_info_pages(call):
    bot.answer_callback_query(call.id)

    if call.data == "info_back_to_menu":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_info_menu(call.message)
        return

    page = call.data.replace("info_", "")
    text = INFO_PAGES.get(page)
    if not text:
        return

    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=get_back_menu(),
            parse_mode="Markdown",
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text=text,
            reply_markup=get_back_menu(),
            parse_mode="Markdown",
        )


# --- СБОР ОБРАЩЕНИЙ ---
@bot.message_handler(func=lambda message: message.text == "⚠️ Сообщить о проблеме")
def choose_category(message):
    user_id = message.from_user.id
    user_data[user_id] = {}

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🏠 Жилищно-бытовые условия / Общежитие", callback_data="category_Жилье"),
        types.InlineKeyboardButton("💼 Трудовые споры / Наставничество", callback_data="category_Работа"),
        types.InlineKeyboardButton("💰 Выплаты / Подъемные / Зарплата", callback_data="category_Деньги"),
        types.InlineKeyboardButton("❓ Другой вопрос", callback_data="category_Другое"),
    )
    bot.send_message(message.chat.id, "Выберите категорию вашей проблемы:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("category_"))
def handle_category_selection(call):
    user_id = call.from_user.id
    category_name = call.data.replace("category_", "")
    user_data[user_id] = {"category": category_name}

    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        f"Вы выбрали категорию: *{category_name}*.\n\n✍️ Пожалуйста, отправьте текст вашего обращения. "
        "Вы также можете прикрепить одно фото.",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_user_report)


def process_user_report(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in user_data or "category" not in user_data[user_id]:
        bot.send_message(chat_id, "⚠️ Ошибка сессии. Нажмите кнопку меню заново.", reply_markup=get_main_menu())
        return

    if message.content_type == "text" and message.text in ["⚠️ Сообщить о проблеме", "ℹ️ Справочная информация"]:
        user_data.pop(user_id, None)
        bot.send_message(chat_id, "📝 Отправка отменена.", reply_markup=get_main_menu())
        return

    photo_id = None
    problem_text = None

    if message.content_type == "photo":
        photo_id = message.photo[-1].file_id
        problem_text = message.caption or "Описание отсутствует."
    elif message.content_type == "text":
        problem_text = message.text
    else:
        msg = bot.send_message(chat_id, "❌ Отправьте текст или картинку.", reply_markup=get_main_menu())
        bot.register_next_step_handler(msg, process_user_report)
        return

    category = user_data[user_id]["category"]
    username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

    admin_message_text = (
        f"🚨 *НОВОЕ ОБРАЩЕНИЕ*\n\n"
        f"👤 *ФИО:* {full_name} ({username})\n"
        f"🆔 *ID:* `{user_id}`\n"
        f"📂 *Категория:* #{category}\n\n"
        f"📝 *Проблема:*\n{problem_text}"
    )

    try:
        if photo_id:
            bot.send_photo(ADMIN_ID, photo_id, caption=admin_message_text, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, admin_message_text, parse_mode="Markdown")
        bot.send_message(
            chat_id,
            "✅ *Ваше обращение отправлено администрации района!*",
            parse_mode="Markdown",
            reply_markup=get_main_menu(),
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")
        bot.send_message(chat_id, "❌ Ошибка отправки. Пожалуйста, попробуйте позже.", reply_markup=get_main_menu())

    user_data.pop(user_id, None)


# --- ЗАПУСК ---
if __name__ == "__main__":
    threading.Thread(target=start_http_server, daemon=True).start()

    try:
        bot.set_my_commands([
            types.BotCommand("/start", "Запустить бота и открыть главное меню"),
            types.BotCommand("/help", "Показать приветствие"),
        ])
    except Exception as e:
        print(f"Ошибка меню команд: {e}")

    print("Инициализация Telegram бота...")
    bot.infinity_polling()
