import telebot
from telebot import types
import http.server
import threading

# НОВЫЙ ТОКЕН ВАШЕГО БОТА (ВСТАВЬТЕ ЕГО ВНУТРЬ КАВЫЧЕК)
API_TOKEN = '8691191999:AAF7Cvci600khCulIk976e7-gzgG0oRMl4E'

# ВАШ ЛИЧНЫЙ TELEGRAM ID (УЖЕ НАСТРОЕН)
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
    user_data[user_id] = {}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_report = types.KeyboardButton("⚠️ Сообщить о проблеме")
    markup.add(btn_report)
    
    welcome_text = (
        "👋 Здравствуйте! Данный бот создан для сбора и оперативного решения "
        "проблемных вопросов молодых специалистов Наровлянского района.\n\n"
        "Вы можете отправить обращение анонимно или оставить свои контакты. "
        "Ваша заявка будет напрямую передана ответственному специалисту."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

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
    
    msg = bot.send_message(
        call.message.chat.id, 
        f"Вы выбрали категорию: **{category}**.\n\n"
        "Пожалуйста, подробно опишите вашу проблему (укажите суть ситуации). "
        "Если хотите остаться анонимным — просто не пишите свое имя в тексте обращения.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_problem_text)

def process_problem_text(message):
    user_id = message.from_user.id
    problem_text = message.text
    
    if user_id not in user_data or 'category' not in user_data[user_id]:
        bot.send_message(message.chat.id, "Пожалуйста, введите /start заново.")
        return

    category = user_data[user_id]['category']
    username = f"@{message.from_user.username}" if message.from_user.username else "Скрыт"
    first_name = message.from_user.first_name or "Не указано"
    
    admin_message = (
        f"🚨 **Поступило новое обращение от молодого специалиста!**\n\n"
        f"📂 **Категория:** {category}\n"
        f"📝 **Суть проблемы:** {problem_text}\n\n"
        f"👤 **Отправитель в Telegram:** {first_name} ({username})"
    )
    
    try:
        bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
        success_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        success_markup.add(types.KeyboardButton("⚠️ Сообщить о проблеме"))
        
        bot.send_message(
            message.chat.id, 
            "✅ Ваше обращение успешно принято и отправлено на рассмотрение в Райисполком. "
            "Мы постараемся разобраться в ситуации в кратчайшие сроки. Спасибо за ваш сигнал!",
            reply_markup=success_markup
        )
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при отправке.")
        print(f"Ошибка: {e}")
        
    user_data.pop(user_id, None)

if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()

    print("Бот успешно запущен...")
    bot.infinity_polling(none_stop=True)
