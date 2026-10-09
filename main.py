import telebot
from telebot import types
import http.server
import threading

# --- НАСТРОЙКИ (ВСТАВЬТЕ СВОЙ ТОКЕН ИЗ ПРОШЛОГО ШАГА) ---
API_TOKEN = '8691191999:AAF7Cvci600khCulIk976e7-gzgG0oRMl4E'
ADMIN_ID = 1099402750

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

# Встроенный веб-сервер для удержания активности Render
def run_web_server():
    server_address = ('', 10000)
    httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)
    print("Вспомогательный веб-сервер запущен...")
    httpd.serve_forever()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data[user_id] = {} # Очистка данных
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_report = types.KeyboardButton("⚠️ Сообщить о проблеме")
    btn_info = types.KeyboardButton("ℹ️ Справочная информация")
    markup.add(btn_report, btn_info)
    
    welcome_text = (
        "👋 Здравствуйте! Данный бот создан для сбора и оперативного решения "
        "проблемных вопросов молодых специалистов Наровлянского района.\n\n"
        "Вы можете отправить обращение (текст + фото) или ознакомиться со "
        "справочной информацией о ваших правах и гарантиях."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# --- БЛОК СПРАВОЧНОЙ ИНФОРМАЦИИ ---
@bot.message_handler(func=lambda message: message.text == "ℹ️ Справочная информация")
def send_info(message):
    info_text = (
        "📚 **Справочник молодого специалиста Республики Беларусь**\n\n"
        "💰 **Денежные выплаты и льготы:**\n"
        "• Выплата денежной помощи (подъемных) в размере месячной стипендии выплачивается нанимателем в течение месяца после заключения договора.\n"
        "• Молодым специалистам, прибывшим по распределению, гарантированы надбавки к тарифным ставкам (окладам) в соответствии с законодательством сферы деятельности.\n"
        "• Предусмотрены льготные кредиты на приобретение домашнего имущества и товаров первой необходимости (согласно Указу Президента № 631).\n\n"
        "🏠 **Жилье:**\n"
        "• Молодые специалисты имеют первоочередное право на получение арендного жилья или места в общежитии.\n"
        "• Возмещение затрат на аренду жилья возможно, если это закреплено в коллективном договоре вашего предприятия.\n\n"
        "📞 **Полезные контакты Наровлянского района:**\n"
        "• Отдел идеологической работы и по делам молодежи Райисполкома: [Контакты администрации]\n"
        "• Наровлянское районное объединение профсоюзов (защита трудовых прав): [Консультация юриста]\n"
        "• Районный комитет ОО 'БРСМ': [Связь с активом]"
    )
    bot.send_message(message.chat.id, info_text, parse_mode="Markdown")

# --- БЛОК СБОРА ОБРАЩЕНИЙ ---
@bot.message_handler(func=lambda message: message.text == "⚠️ Сообщить о проблеме")
def choose_category(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("🏠 Жилищно-бытовые условия / Общежитие", callback_data="category_Жилье")
    btn2 = types.InlineKeyboardButton("💼 Трудовые споры / Наставничество", callback_data="category_Работа")
    btn3 = types.InlineKeyboardButton("💰 Выплаты / Подъемные / Зарплата", callback_data="category_Деньги")
    btn4 = types.InlineKeyboardButton("❓ Другой вопрос", callback_data="category_Другое")
    markup.add(btn1, btn2, btn3, btn4)
    
    bot.send_message(message.chat.id, "Выберите категорию вашей проблемы:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
def save_category(call):
    user_id = call.from_user.id
    category = call.data.split('_')[1]
    
    user_data[user_id] = {'category': category}
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("❌ Отмена"))
    
    msg = bot.send_message(
        call.message.chat.id, 
        f"Вы выбрали категорию: **{category}**.\n\n"
        "✍️ Пожалуйста, отправьте описание вашей проблемы.\n"
        "Вы можете прикрепить к сообщению ОДНО ФОТО (как в обычном чате) или отправить просто текст.",
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_problem_data)

def process_problem_data(message):
    user_id = message.from_user.id
    
    if message.text == "❌ Отмена":
        send_welcome(message)
        return

    if user_id not in user_data or 'category' not in user_data[user_id]:
        bot.send_message(message.chat.id, "Пожалуйста, введите /start заново.")
        return

    category = user_data[user_id]['category']
    username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
    first_name = message.from_user.first_name or "Не указано"
    
    problem_text = ""
    photo_id = None
    
    # Если пользователь прислал фото с текстом
    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
        problem_text = message.caption if message.caption else "[Фото без текстового описания]"
    elif message.content_type == 'text':
        problem_text = message.text
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте текст или фотографию.")
        return

    # Формируем отчет для вас (Администратора)
    admin_message = (
        f"🚨 **Поступило новое обращение от молодого специалиста!**\n\n"
        f"📂 **Категория:** {category}\n"
        f"📝 **Суть проблемы:** {problem_text}\n\n"
        f"👤 **Отправитель в Telegram:** {first_name} ({username})"
    )
    
    try:
        # Если есть фото, отправляем фото с описанием, если нет — только текст
        if photo_id:
            bot.send_photo(ADMIN_ID, photo_id, caption=admin_message, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
        
        # Возвращаем стандартные кнопки
        success_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        success_markup.add(types.KeyboardButton("⚠️ Сообщить о проблеме"), types.KeyboardButton("ℹ️ Справочная информация"))
        
        bot.send_message(
            message.chat.id, 
            "✅ Ваше обращение успешно принято и отправлено на рассмотрение в Райисполком. "
            "Мы постараемся разобраться в ситуации в кратчайшие сроки. Спасибо за ваш сигнал!",
            reply_markup=success_markup
        )
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при отправке. Попробуйте позже.")
        print(f"Ошибка: {e}")
        
    user_data.pop(user_id, None)

if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()

    print("Бот успешно обновлен и запущен...")
    bot.infinity_polling(none_stop=True)
