import os
import re
import threading
import requests
import telebot
from telebot import types
from flask import Flask

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

# --- ВЕБ-СЕРВЕР НА FLASK ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "OK", 200

def run_flask():
    # Запускаем Flask на нужном порту
    app.run(host="0.0.0.0", port=PORT)

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
    "Помогаешь с вопросами о трудовых правах, выплатах, льготах, распределении после ВУЗа/СУЗа, "
    "жилищных условиях, больничных и т.п. Опирайся на Трудовой кодекс Республики Беларусь, "
    "Кодекс об образовании, Указ Президента № 1 от 05.01.2024 и другие нормативные акты РБ. "
    "Отвечай кратко, по делу, дружелюбно. Если вопрос юридический и сложный — советуй "
    "уточнить у нанимателя, в профсоюзе или в управлении по труду. "
    "Не выдумывай суммы и нормы, если не уверен.\n\n"
    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:\n"
    "- добавлять ссылки на каналы, группы, сайты и сторонние ресурсы;\n"
    "- предлагать подписаться, перейти куда-либо или обратиться в чат;\n"
    "- вставлять @упоминания и любые URL;\n"
    "- добавлять рекламные приписки в конце ответа.\n"
    "Отвечай только текстом по существу вопроса."
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

    if len(answer) > 4000:
        answer = answer[:4000] + "..."
    return answer

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
        "📝 Пожалуйста, подробно **опишите вашу проблему** или отправьте обращение одним сообщением. "
        "Вы можете прикрепить фото или документ, если необходимо.\n\n"
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
        "🤖 **Режим ИИ активирован.**\n"
        "Задайте любой интересующий вас вопрос по поводу трудовых правах в РБ.",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "🧹 Очистить диалог с ИИ")
def clear_ai_history(message):
    user_id = message.from_user.id
    chat_history.pop(user_id, None)
    bot.send_message(message.chat.id, "🧹 История вашего диалога с ИИ успешно очищена!")

# --- БАЗА ДАННЫХ СТРАНИЦ СПРАВОЧНИКА ---
INFO_PAGES = {
    "docs": (
        "📋 *Документы при приёме на работу*\n\n"
        "*Основание:* ст. 26 Трудового кодекса Республики Беларусь, "
        "Указ Президента № 1 от 05.01.2024.\n\n"
        "*Обязательные документы:*\n"
        "✔️ Паспорт или ID-карта гражданина РБ\n"
        "✔️ Трудовая книжка (при наличии)\n"
        "✔️ Документ об образовании (диплом)\n"
        "✔️ Свидетельство о направлении на работу\n"
        "✔️ Документы воинского учёта\n"
        "✔️ Медицинская справка о состоянии здоровья\n"
        "✔️ Страховое свидетельство ФСЗН\n\n"
        "*Запрещено требовать:*\n"
        "▪️ Документы, не предусмотренные законодательством\n"
        "▪️ Характеристики с прежних мест работы\n"
        "▪️ Справки о жилищных условиях\n\n"
        "*Важно:* приём оформляется приказом, трудовой договор — в письменной форме (ст. 18 ТК)."
    ),
    "boss": (
        "🤝 *Обязанности нанимателя при приёме*\n\n"
        "*Основание:* ст. 54, 55 Трудового кодекса РБ.\n\n"
        "*Наниматель обязан:*\n"
        "✔️ Заключить трудовой договор в письменной форме\n"
        "✔️ Издать приказ о приёме на работу\n"
        "✔️ Ознакомить работника под подпись с условиями труда\n"
        "✔️ Ознакомить с коллективным договором и ПВТР\n"
        "✔️ Провести инструктаж по охране труда (ст. 226 ТК)\n"
        "✔️ Организовать стажировку молодого специалиста\n"
        "✔️ Вести трудовую книжку\n"
    ),
    "pension": "🎓 *Распределение и пенсионный стаж*\n\nПериод обучения на дневной форме засчитывается в общий стаж, но не входит в страховой стаж для назначения пенсии, так как в этот период не уплачиваются взносы в ФСЗН. Однако период работы по распределению полностью формирует ваш полноценный пенсионный и страховой стаж.",
    "test": "🚫 *Испытательный срок*\n\nСогласно ст. 28 Трудового кодекса РБ, предварительное испытание при приеме на работу **не устанавливается** для молодых специалистов, получивших профессионально-техническое, среднее специальное, высшее или научно-ориентированное образование и направленных на работу по распределению.",
    "sick": "🤒 *Расчет больничного для новичков*\n\nДля молодых специалистов предусмотрены льготные условия. Пособие по временной нетрудоспособности с первого дня болезни исчисляется в размере **100 процентов** среднедневного заработка (в отличие от общего правила 80%), если право на больничный возникло в период отработки.",
