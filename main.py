import telebot
from telebot import types
import http.server
import threading
import sys

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
API_TOKEN = '8691191999:AAF7Cvci600khCulIk976e7-gzgG0oRMl4E'
ADMIN_ID = 1099402750

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

# Вспомогательный веб-сервер для Render (занимает главный поток, как требует хостинг)
class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Отключаем спам логов от проверок Render
        
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")

def start_http_server():
    server_address = ('0.0.0.0', 10000)
    try:
        httpd = http.server.HTTPServer(server_address, SilentHandler)
        print("Вспомогательный веб-сервер запущен на порту 10000...")
        httpd.serve_forever()
    except Exception as e:
        print(f"Критическая ошибка веб-сервера: {e}")
        sys.exit(1)

# --- КОМАНДА СТАРТ ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_report = types.KeyboardButton("⚠️ Сообщить о проблеме")
    btn_info = types.KeyboardButton("ℹ️ Справочная информация")
    markup.add(btn_report, btn_info)
    
    welcome_text = (
        "👋 Здравствуйте! Данный bot создан для сбора и оперативного решения "
        "проблемных вопросов молодых специалистов Наровлянского района.\n\n"
        "Вы можете отправить обращение (текст + фото) или ознакомиться со "
        "справочной информацией о ваших правах, выплатах и гарантиях."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# --- ГЛАВНОЕ МЕНЮ СПРАВОЧНИКА ---
@bot.message_handler(func=lambda message: message.text == "ℹ️ Справочная информация")
def send_info_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 Документы при приеме на работу", callback_data="info_docs"),
        types.InlineKeyboardButton("🤝 Обязанности нанимателя при приеме", callback_data="info_boss"),
        types.InlineKeyboardButton("🎓 Распределение и пенсионный стаж", callback_data="info_pension"),
        types.InlineKeyboardButton("🚫 Кому не ставится испытательный срок", callback_data="info_test"),
        types.InlineKeyboardButton("🤒 Расчет больничного для новичков", callback_data="info_sick"),
        types.InlineKeyboardButton("❓ ТОП Вопросов молодых специалистов", callback_data="info_faq")
    )
    bot.send_message(message.chat.id, "📚 **Памятка молодого специалиста**\n\nВыберите интересующую вас тему из интерактивного меню:", reply_markup=markup)

# --- ОБРАБОТЧИК КНОПОК СПРАВОЧНИКА ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('info_'))
def handle_info_pages(call):
    bot.answer_callback_query(call.id)
    if call.data == "info_back_to_menu":
        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception:
            pass
        send_info_menu(call.message)
        return

    page = call.data.replace("info_", "")
    text = ""
    
    if page == "docs":
        text = "📋 **Какие документы нужно предъявить нанимателю?**\n\n✔️ Паспорт / ID-карта\n✔️ Документы воинского учета\n✔️ Диплом\n✔️ Свидетельство о направлении\n✔️ Медсправка"
    elif page == "boss":
        text = "🤝 **Обязанности нанимателя:**\n\n✔️ Заключить договор\n✔️ Оформить приказ\n✔️ Ознакомить с обязанностями под подпись\n✔️ Провести инструктаж по охране труда"
    elif page == "pension":
        text = "🎓 **Стаж:**\n\n✅ Время учебы дневной — общий стаж.\n✅ Отработка — страховой стаж (идут взносы ФСЗН)."
    elif page == "test":
        text = "🚫 **Испытательный срок не ставится:**\n\n▪️ Молодым специалистам после ВУЗов/СУЗов\n▪️ Лицам до 18 лет\n▪️ При переводе к другому нанимателю"
    elif page == "sick":
        text = "🤒 **Больничный с 1 июля 2024:**\n\nМинимум привязан к МЗП (726 руб). За полный месяц болезни — 100% от МЗП."
    elif page == "faq":
        text = "❓ **Вопросы:**\n\n1. Выходить 1 августа.\n2. Декрет и армия входят в срок отработки.\n3. По собственному желанию уволиться нельзя."

    back_markup = types.InlineKeyboardMarkup()
    back_markup.add(types.InlineKeyboardButton("🔙 Вернуться в меню", callback_data="info_back_to_menu"))
    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=back_markup, parse_mode="Markdown")
    except Exception:
        bot.send_message(call.message.chat.id, text=text, reply_markup=back_markup, parse_mode="Markdown")

# --- БЛОК СБОРА ОБРАЩЕНИЙ ---
@bot.message_handler(func=lambda message: message.text == "⚠️ Сообщить о проблеме")
def choose_category(message):
    user_id = message.from_user.id
    user_data[user_id] = {}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🏠 Жилищно-бытовые условия / Общежитие", callback_data="category_Жилье"),
        types.InlineKeyboardButton("💼 Трудовые споры / Наставничество", callback_data="category_Работа"),
        types.InlineKeyboardButton("💰 Выплаты / Подъемные / Зарплата", callback_data="category_Деньги"),
        types.InlineKeyboardButton("❓ Другой вопрос", callback_data="category_Другое")
    )
    bot.send_message(message.chat.id, "Выберите категорию вашей проблемы:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
def handle_category_selection(call):
    user_id = call.from_user.id
    category_name = call.data.replace("category_", "")
    user_data[user_id] = {'category': category_name}
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id, 
        f"Вы выбрали категорию: **{category_name}**.\n\n✍️ Пожалуйста, отправьте текст вашего обращения. Вы также можете прикрепить одно фото.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_user_report)

def process_user_report(message):
    user_id = message.from_user.id
    if user_id not in user_data or 'category' not in user_data[user_id]:
        bot.send_message(message.chat.id, "⚠️ Ошибка сессии. Нажмите кнопку меню заново.")
        return

    photo_id = None
    problem_text = "Описание отсутствует."

    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
        if message.caption:
            problem_text = message.caption
            
    if message.content_type == 'text':
        if message.text in ["⚠️ Сообщить о проблеме", "ℹ️ Справочная информация"]:
            bot.send_message(message.chat.id, "📝 Отправка отменена.")
            return
        problem_text = message.text

    if message.content_type != 'photo' and message.content_type != 'text':
        msg = bot.send_message(message.chat.id, "❌ Отправьте текст или картинку.")
        bot.register_next_step_handler(msg, process_user_report)
        return

    category = user_data[user_id]['category']
    username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

    admin_message_text = f"🚨 **НОВОЕ ОБРАЩЕНИЕ**\n\n👤 **ФИО:** {full_name} ({username})\n🆔 **ID:** `{user_id}`\n📂 **Категория:** #{category}\n\n📝 **Проблема:**\n{problem_text}"

    try:
        if photo_id:
            bot.send_photo(ADMIN_ID, photo_id, caption=admin_message_text, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, admin_message_text, parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ **Ваше обращение отправлено администрации района!**", parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка отправки. Пожалуйста, попробуйте позже.")

    if user_id in user_data:
        del user_data[user_id]

if __name__ == '__main__':
    try:
        bot.set_my_commands([
            types.BotCommand("/start", "Запустить бота и открыть главное меню"),
            types.BotCommand("/help", "Показать приветствие")
        ])
    except Exception as e:
        print(f"Ошибка меню команд: {e}")

    print("Инициализация Telegram бота...")
    bot_thread = threading.Thread(target=bot.infinity_polling)
    bot_thread.daemon = True
    bot_thread.start()
    print("Поллинг Telegram бота успешно запущен.")

    start_http_server()
