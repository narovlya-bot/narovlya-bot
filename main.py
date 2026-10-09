import telebot
from telebot import types
import http.server
import threading

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
API_TOKEN = '8691191999:AAF7Cvci600khCulIk976e7-gzgG0oRMl4E'
ADMIN_ID = 1099402750

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def run_web_server():
    server_address = ('', 10000)
    httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)
    print("Вспомогательный веб-сервер Render запущен...")
    httpd.serve_forever()

# --- КОМАНДА СТАРТ ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data.clear()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_report = types.KeyboardButton("⚠️ Сообщить о проблеме")
    btn_info = types.KeyboardButton("ℹ️ Справочная информация")
    markup.add(btn_report, btn_info)
    
    welcome_text = (
        "👋 Здравствуйте! Данный бот создан для сбора и оперативного решения "
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
    
    bot.send_message(
        message.chat.id, 
        "📚 **Памятка молодого специалиста**\n\n"
        "Выберите интересующую вас тему из интерактивного меню:", 
        reply_markup=markup
    )

# --- ОБРАБОТЧИК КНОПОК СПРАВОЧНИКА ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('info_'))
def handle_info_pages(call):
    if call.data == "info_back_to_menu":
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        send_info_menu(call.message)
        return

    page = call.data.replace("info_", "")
    text = ""
    
    if page == "docs":
        text = (
            "📋 **Какие документы нужно предъявить нанимателю?**\n\n"
            "✔️ Паспорт / ID-карта\n"
            "✔️ Документы воинского учета (для призывников)\n"
            "✔️ Диплом / Документ об образовании\n"
            "✔️ Свидетельство о направлении на работу\n"
            "✔️ Медицинская справка о состоянии здоровья\n"
            "✔️ Иные документы по закону\n\n"
            "‼️ Молодые специалисты, впервые поступающие на работу, трудовую книжку и страховое свидетельство не представляют (их оформляет сам наниматель)."
        )
    elif page == "boss":
        text = (
            "🤝 **Обязанности нанимателя при приеме молодого специалиста:**\n\n"
            "✔️ Заключить трудовой договор/контракт в письменной форме\n"
            "✔️ Оформить приказ о приеме и ознакомить под подпись\n"
            "✔️ Ознакомить с обязанностями, условиями и оплатой труда\n"
            "✔️ Ознакомить с коллективным договором и внутренним распорядком\n"
            "✔️ Провести вводный инструктаж по охране труда\n"
            "✔️ Завести трудовую книжку и оформить свидетельство ФСЗН\n\n"
            "❗️ Все ознакомления производятся исключительно под подпись работника."
        )
    elif page == "pension":
        text = (
            "🎓 **Распределение и пенсионный стаж**\n\n"
            "📚 **Время учебы на дневном:**\n"
            "✅ Включается в ОБЩИЙ трудовой стаж.\n"
            "❌ НЕ включается в СТРАХОВОЙ стаж.\n\n"
            "💼 **Отработка по распределению:**\n"
            "✅ Включается в СТРАХОВОЙ стаж (так как платятся взносы в ФСЗН).\n\n"
            "💡 **Условия для пенсии по возрасту:**\n"
            "➡️ Общий стаж: Мужчины - от 25 лет, Женщины - от 20 лет.\n"
            "➡️ Пенсионный возраст: Мужчины - 63 года, Женщины - 58 лет.\n"
            "➡️ Страховой стаж: Требуется не менее 20 лет."
        )
    elif page == "test":
        text = (
            "🚫 **Кому НЕ устанавливается предварительное испытание?**\n\n"
            "Испытательный срок при приеме не ставится:\n"
            "▪️ Молодым специалистам, получившим проф-техническое, среднее специальное или высшее образование\n"
            "▪️ Работникам младше 18 лет\n"
            "▪️ Людям с инвалидностью\n"
            "▪️ Временным и сезонным работникам\n"
            "▪️ При переводе к другому нанимателю или в другую местность\n"
            "▪️ При приеме на работу по конкурсу"
        )
    elif page == "sick":
        text = (
            "🤒 **Расчет больничного для новичков (с 1 июля 2024 года):**\n\n"
            "✅ Минимальная база для расчета теперь привязана к минимальной заработной плате (МЗП) - сейчас это 726 руб.\n"
            "✅ Больничный за полный месяц болезни считается как 100% от МЗП.\n"
            "📈 Если ваш средний реальный заработок станет выше расчетной базы МЗП, больничный будет рассчитываться как 80% от вашего фактического заработка.\n"
            "🏆 100% от реального заработка выплачивается при общем стаже работы от 10 лет и более."
        )
    elif page == "faq":
        text = (
            "❓ **ТОП Вопросов молодых специалистов:**\n\n"
            "1⃣ **Когда выходить?** 1 августа. Если начнете работать раньше, срок отработки пойдет с даты договора.\n"
            "2⃣ **Повышение?** Да, если новая должность связана с вашей специальностью.\n"
            "3⃣ **Декрет и армия?** Полностью входят в срок отработки по распределению.\n"
            "4⃣ **Можно уволиться?** ❌ По собственному желанию или соглашению сторон - нельзя. Увольнение возможно только при ликвидации фирмы, по состоянию здоровья или за грубые нарушения.\n"
            "5⃣ **Выплаты:** Подъемные (1 стипендия в первый месяц), пособие за переезд (1 оклад), ежемесячные надбавки в бюджете (от 10% до 50% оклада).\n"
            "6⃣ **Льготный кредит:** На бел. товары под 25% от ставки рефинансирования на сумму до 30 БПМ."
        )

    back_markup = types.InlineKeyboardMarkup()
    back_markup.add(types.InlineKeyboardButton("🔙 Вернуться в меню справочника", callback_data="info_back_to_menu"))
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=back_markup)

# --- БЛОК СБОРА ОБРАЩЕНИЙ ---
@bot.message_handler(func=lambda message: message.text == "⚠️ Сообщить о проблеме")
def choose_category(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🏠 Жилищно-бытовые условия / Общежитие", callback_data="category_Жилье"),
        types.InlineKeyboardButton("💼 Трудовые споры / Наставничество", callback_data="category_Работа"),
        types.InlineKeyboardButton("💰 Выплаты / Подъемные / Зарплата", callback_data="category_Деньги"),
        types.InlineKeyboardButton("❓ Другой вопрос", callback_data="category_Другое")
    )
    bot.send_message(message.chat.id, "Выберите категорию вашей проблемы:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
def save_category(call):
    user_id = call.from_user.id
    category = call.data.replace("category_", "")
    
    user_data[user_id] = {'category': category}
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("❌ Отмена"))
    
    msg = bot.send_message(
        call.message.chat.id, 
        f"Вы выбрали категорию: **{category}**.\n\n"
        "✍️ Пожалуйста, отправьте подробное описание вашей ситуации.\n"
        "Вы можете прикрепить к сообщению **одно фото** или прислать просто текст проблемы.",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_problem_data)

def process_problem_data(message):
    user_id = message.from_user.id
    
    if message.text == "❌ Отмена":
        send_welcome(message)
        return

    if user_id not in user_data or 'category' not in user_data[user_id]:
        bot.send_message(message.chat.id, "Что-то пошло не так. Пожалуйста, введите /start заново.")
        return

    category = user_data[user_id]['category']
    username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
    first_name = message.from_user.first_name or "Не указано"
    
    problem_text = ""
    photo_id = None
    
    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
        problem_text = message.caption if message.caption else "[Фото без текстового описания]"
    elif message.content_type == 'text':
        problem_text = message.text
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте текст или фотографию.")
        return

    admin_message = (
        f"🚨 **Поступило новое обращение от молодого специалиста!**\n\n"
        f"📂 **Категория:** {category}\n"
        f"📝 **Суть проблемы:** {problem_text}\n\n"
        f"👤 **Отправитель в Telegram:** {first_name} ({username})"
    )
    
    try:
        if photo_id:
            bot.send_photo(ADMIN_ID, photo_id, caption=admin_message)
        else:
            bot.send_message(ADMIN_ID, admin_message)
        
