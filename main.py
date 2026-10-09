import os
import re
import http.server
import threading
import requests
import telebot
from telebot import types

# --- НАСТРОЙКИ ---
API_TOKEN = "НОВЫЙ_ТОКЕН_ИЗ_BOTFATHER"
ADMIN_ID = 1099402750
PORT = int(os.environ.get("PORT", "10000"))

# --- НЕЙРОСЕТЬ (OpenRouter) ---
OPENROUTER_API_KEY = "sk-or-v1-ВАШ_КЛЮЧ_СЮДА"
AI_MODEL = "google/gemini-2.0-flash-exp:free"
AI_URL = "https://openrouter.ai"

bot = telebot.TeleBot(API_TOKEN)
user_data = {}
chat_history = {}
MAX_HISTORY = 10

# --- ЗАЩИТА ОТ ССЫЛОК (только для ИИ) ---
URL_PATTERNS = [
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"www\.\S+", re.IGNORECASE),
    re.compile(r"t\.me/\S+", re.IGNORECASE),
    re.compile(r"telegram\.me/\S+", re.IGNORECASE),
    re.compile(r"\B@[A-Za-z0-9_]{3,}\b"),
    re.compile(r"подпишись\S*", re.IGNORECASE),
    re.compile(r"подписаться", re.IGNORECASE),
    re.compile(r"переходи\S*", re.IGNORECASE),
    re.compile(r"присоединяйся", re.IGNORECASE),
    re.compile(r"наш канал", re.IGNORECASE),
    re.compile(r"наш чат", re.IGNORECASE),
]

def strip_links(text: str) -> str:
    if not text:
        return ""
    for pattern in URL_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# --- НЕУБИВАЕМЫЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ---
class RenderHealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Отключаем спам логов в консоль Render

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Бот активен и работает!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_health_server():
    server_address = ("0.0.0.0", PORT)
    # Используемallow_reuse_address, чтобы порт не блокировался при перезапусках
    httpd = http.server.HTTPServer(server_address, RenderHealthCheckHandler)
    httpd.serve_forever()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton("⚠️ Сообщить о проблеме"),
        types.KeyboardButton("ℹ️ Справочная информация"),
        types.KeyboardButton("🤖 Задать вопрос ИИ"),
        types.KeyboardButton("🧹 Очистить диалог с ИИ"),
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
        types.InlineKeyboardButton("📞 Контакты", callback_data="info_contacts"),
        types.InlineKeyboardButton("⚖️ Правовая база", callback_data="info_law"),
    )
    return markup

def get_back_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Вернуться в меню", callback_data="info_back_to_menu"))
    return markup

# --- НЕЙРОСЕТЬ ---
SYSTEM_PROMPT = (
    "Ты — виртуальный помощник для молодых специалистов Наровлянского района (Беларусь). "
    "Помогаешь с вопросами о трудовых правах, выплатах, льготах, распределении после ВУЗа/СУЗа. "
    "Опирайся на Трудовой кодекс Республики Беларусь.\n"
    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО добавлять ссылки, рекламу и юзернеймы."
)

def ask_ai(user_message: str, user_id: int) -> str:
    history = chat_history.setdefault(user_id, [])
    history.append({"role": "user", "content": user_message})

    if len(history) > MAX_HISTORY:
        history[:] = history[-MAX_HISTORY:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com",
        "X-Title": "Narovlya Bot",
    }
    payload = {"model": AI_MODEL, "messages": messages}

    try:
        r = requests.post(AI_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        answer = data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[AI] Ошибка: {e}", flush=True)
        return "⚠️ Извините, не удалось получить ответ. Попробуйте позже."

    answer = strip_links(answer)
    history.append({"role": "assistant", "content": answer})
    return answer[:4000]

# --- ОБРАБОТЧИКИ КОМАНД ---
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    user_id = message.from_user.id
    user_data.pop(user_id, None)
    welcome_text = (
        "👋 Здравствуйте! Данный бот создан для сбора и оперативного решения "
        "проблемных вопросов молодых специалистов Наровлянского района.\n\n"
        "Вы можете:\n"
        "• отправить обращение — кнопка *⚠️ Сообщить о проблеме*;\n"
        "• открыть справочник — кнопка *ℹ️ Справочная информация*;\n"
        "• задать вопрос ИИ — кнопка *🤖 Задать вопрос ИИ*."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⚠️ Сообщить о проблеме")
def report_issue_init(message):
    user_id = message.from_user.id
    user_data[user_id] = "waiting_for_issue"
    bot.send_message(
        message.chat.id,
        "📝 Пожалуйста, подробно **опишите вашу проблему** или отправьте обращение одним сообщением.\n\n"
        "Администрация района обязательно рассмотрит его.",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "ℹ️ Справочная информация")
def send_info_menu(message):
    user_id = message.from_user.id
    user_data.pop(user_id, None)
    bot.send_message(
        message.chat.id,
        "📚 *Памятка молодого специалиста*\n\nВыберите интересующую вас тему:",
        reply_markup=get_info_menu(),
        parse_mode="Markdown",
    )

@bot.message_handler(func=lambda message: message.text == "🤖 Задать вопрос ИИ")
def ai_mode_init(message):
    user_id = message.from_user.id
    user_data[user_id] = "ai_mode"
    bot.send_message(
        message.chat.id,
        "🤖 **Режим ИИ активирован.**\nЗадайте любой вопрос по поводу трудовых прав в РБ.",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "🧹 Очистить диалог с ИИ")
def clear_ai_history(message):
    user_id = message.from_user.id
    chat_history.pop(user_id, None)
    bot.send_message(message.chat.id, "🧹 История вашего диалога с ИИ успешно очищена!")

# --- БАЗА ДАННЫХ СТРАНИЦ СПРАВОЧНИКА ---
INFO_PAGES = {
    "docs": "📋 *Документы при приёме на работу*\n\nПаспорт, трудовая книжка, диплом, направление на работу, медсправка.",
    "boss": "🤝 *Обязанности нанимателя*\n\nЗаключить договор, ознакомить с условиями труда под подпись, провести инструктаж.",
    "pension": "🎓 *Распределение и стаж*\n\nПериод отработки по распределению полностью формирует ваш страховой пенсионный стаж.",
    "test": "🚫 *Испытательный срок*\n\nМолодым специалистам по распределению испытательный срок **не устанавливается** (ст. 28 ТК РБ).",
    "sick": "🤒 *Расчет больничного*\n\nПособие исчисляется в размере **100%** среднедневного заработка с первого дня болезни.",
    "faq": "❓ *ТОП Вопросов*\n\nПерераспределение возможно только при согласии ведомства и наличии законных оснований.",
    "contacts": "📞 *Контакты*\n\nУправление по труду Наровлянского РИК: [Укажите телефон].",
    "law": "⚖️ *Правовая база*\n\nТрудовой кодекс РБ, Кодекс об образовании, Указ Президента №1."
}

@bot.callback_query_handler(func=lambda call: call.data.startswith("info_"))
def handle_info_menu_clicks(call):
    page_key = call.data.replace("info_", "")
    if page_key == "back_to_menu":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📚 *Памятка молодого специалиста*\n\nВыберите интересующую вас тему:",
            reply_markup=get_info_menu(),
            parse_mode="Markdown"
        )
    else:
        text_content = INFO_PAGES.get(page_key, "⚠️ Раздел находится в разработке.")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text_content,
            reply_markup=get_back_menu(),
            parse_mode="Markdown"
        )
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'document'])
def handle_user_inputs(message):
    user_id = message.from_user.id
    current_state = user_data.get(user_id)

    if current_state == "waiting_for_issue":
        try:
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
            bot.send_message(ADMIN_ID, f"☝️ Обращение от пользователя:\nID: `{user_id}`")
            user_data.pop(user_id, None)
            bot.send_message(message.chat.id, "✅ **Ваше обращение принято.**", reply_markup=get_main_menu(), parse_mode="Markdown")
        except Exception as e:
            print(f"[ERR] Не удалось переслать админу: {e}")
            bot.send_message(message.chat.id, "⚠️ Ошибка отправки. Попробуйте позже.")

    elif current_state == "ai_mode":
        if message.content_type != 'text':
            bot.send_message(message.chat.id, "🤖 Нужен текстовый вопрос.")
            return
