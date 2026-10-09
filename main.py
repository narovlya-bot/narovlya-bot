import os
import re
import http.server
import threading
import requests
import telebot
from telebot import types


# --- НАСТРОЙКИ ---
API_TOKEN = "ВСТАВЬТЕ_НОВЫЙ_ТОКЕН_ИЗ_BOTFATHER"
ADMIN_ID = 1099402750
PORT = int(os.environ.get("PORT", "10000"))

# --- НЕЙРОСЕТЬ (OpenRouter) ---
OPENROUTER_API_KEY = "sk-or-v1-ВАШ_КЛЮЧ_СЮДА"
AI_MODEL = "google/gemini-2.0-flash-exp:free"
AI_URL = "https://openrouter.ai/api/v1/chat/completions"

bot = telebot.TeleBot(API_TOKEN)
user_data = {}
chat_history = {}
MAX_HISTORY = 10


# --- ЗАЩИТА ОТ ССЫЛОК (только для ответов ИИ) ---
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


# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
class RenderHealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Бот активен и работает!".encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


def run_health_server():
    server_address = ("0.0.0.0", PORT)
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
    "Опирайся на Трудовой кодекс Республики Беларусь, Кодекс об образовании, Указ Президента № 1 от 05.01.2024. "
    "Отвечай кратко, по делу. Не выдумывай суммы и нормы, если не уверен.\n"
    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО добавлять ссылки, рекламу, юзернеймы каналов и @упоминания."
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
    print(f"[START] {user_id}", flush=True)

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
    print(f"[REPORT] {user_id}", flush=True)
    bot.send_message(
        message.chat.id,
        "📝 Пожалуйста, подробно **опишите вашу проблему** одним сообщением. "
        "Можно приложить фото.\n\n"
        "Администрация района обязательно рассмотрит обращение.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda message: message.text == "ℹ️ Справочная информация")
def send_info_menu(message):
    user_id = message.from_user.id
    user_data.pop(user_id, None)
    print(f"[INFO] {user_id}", flush=True)
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
    print(f"[AI_MODE] {user_id}", flush=True)
    bot.send_message(
        message.chat.id,
        "🤖 **Режим ИИ активирован.**\nЗадайте любой вопрос по трудовым правам в РБ.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda message: message.text == "🧹 Очистить диалог с ИИ")
def clear_ai_history(message):
    user_id = message.from_user.id
    chat_history.pop(user_id, None)
    print(f"[AI_CLEAR] {user_id}", flush=True)
    bot.send_message(message.chat.id, "🧹 История вашего диалога с ИИ очищена.", reply_markup=get_main_menu())


# --- СПРАВОЧНИК ---
INFO_PAGES = {
    "docs": (
        "📋 *Документы при приёме на работу*\n\n"
        "✔️ Паспорт или ID-карта\n"
        "✔️ Трудовая книжка (при наличии)\n"
        "✔️ Диплом\n"
        "✔️ Свидетельство о направлении на работу\n"
        "✔️ Документы воинского учёта\n"
        "✔️ Медицинская справка\n"
        "✔️ Страховое свидетельство ФСЗН\n\n"
        "*Основание:* ст. 26 ТК РБ."
    ),
    "boss": (
        "🤝 *Обязанности нанимателя при приёме*\n\n"
        "✔️ Заключить трудовой договор в письменной форме\n"
        "✔️ Издать приказ о приёме\n"
        "✔️ Ознакомить с обязанностями и условиями труда под подпись\n"
        "✔️ Провести инструктаж по охране труда\n"
        "✔️ Организовать стажировку молодого специалиста\n\n"
        "*Основание:* ст. 54, 55, 226 ТК РБ."
    ),
    "pension": (
        "🎓 *Распределение и пенсионный стаж*\n\n"
        "✅ Время очной учёбы — в общий стаж\n"
        "✅ Работа по распределению — в страховой стаж (взносы ФСЗН)\n"
        "✅ Служба в армии входит в срок отработки\n"
        "✅ Отпуск по уходу за ребёнком до 3 лет входит в срок отработки\n\n"
        "*Сроки:* ВУЗ — 2 года, СУЗ — 1 год."
    ),
    "test": (
        "🚫 *Испытательный срок*\n\n"
        "Молодым специалистам по распределению испытательный срок "
        "**не устанавливается**.\n\n"
        "Также не ставится: лицам до 18 лет, беременным, женщинам с детьми до 3 лет, "
        "при переводе к другому нанимателю, инвалидам.\n\n"
        "*Основание:* ст. 28 ТК РБ."
    ),
    "sick": (
        "🤒 *Расчёт больничного*\n\n"
        "▪️ Первые 12 дней — 80% среднедневного заработка\n"
        "▪️ С 13-го дня — 100%\n"
        "▪️ Минимум за месяц — 100% МЗП\n\n"
        "*100% с первого дня:* беременность и роды, уход за ребёнком до 3 лет, "
        "профзаболевание, травма на производстве."
    ),
    "faq": (
        "❓ *ТОП вопросов молодых специалистов*\n\n"
        "*1. Когда выходить?* — Как правило, с 1 августа.\n\n"
        "*2. Можно ли уволиться?* — До окончания отработки только по уважительным причинам.\n\n"
        "*3. Декрет в отработку?* — Да, входит.\n\n"
        "*4. Армия в отработку?* — Да, входит.\n\n"
        "*5. Нет работы по специальности?* — Обратитесь в управление по труду.\n\n"
        "*6. Кто платит за переезд?* — Наниматель + подъёмные.\n\n"
        "*7. Льготы?* — Подъёмные, компенсация переезда, льготные кредиты, общежитие."
    ),
    "contacts": (
        "📞 *Контакты*\n\n"
        "*Управление по труду, занятости и соцзащите Наровлянского райисполкома*\n"
        "📍 г. Наровля, ул. Ленина, 1\n"
        "☎️ Уточните актуальный номер в райисполкоме.\n\n"
        "*Наровлянский райисполком*\n"
        "📍 г. Наровля\n\n"
        "*Профсоюзная организация* — по месту работы.\n\n"
        "*Экстренные службы:* 101, 102, 103"
    ),
    "law": (
        "⚖️ *Правовая база*\n\n"
        "📘 *Трудовой кодекс РБ* — ст. 18, 20, 26, 28, 54, 55, 226\n"
        "📗 *Кодекс об образовании РБ* — ст. 83 (освобождение от отработки)\n"
        "📙 *Указ Президента № 1 от 05.01.2024* — правила приёма на работу\n"
        "📕 *Постановление Минтруда № 74 от 23.08.2011* — о стажировке\n"
        "📓 *Закон «О пособиях по временной нетрудоспособности»* и Постановление Совмина № 569"
    ),
}


@bot.callback_query_handler(func=lambda call: call.data.startswith("info_"))
def handle_info_menu_clicks(call):
    bot.answer_callback_query(call.id)
    page_key = call.data.replace("info_", "")

    if page_key == "back_to_menu":
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="📚 *Памятка молодого специалиста*\n\nВыберите интересующую вас тему:",
                reply_markup=get_info_menu(),
                parse_mode="Markdown",
            )
        except Exception:
            send_info_menu(call.message)
    else:
        text_content = INFO_PAGES.get(page_key, "⚠️ Раздел находится в разработке.")
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text_content,
                reply_markup=get_back_menu(),
                parse_mode="Markdown",
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                text_content,
                reply_markup=get_back_menu(),
                parse_mode="Markdown",
            )


# --- ОБРАБОТКА ВВОДА ПОЛЬЗОВАТЕЛЯ ---
@bot.message_handler(func=lambda message: True, content_types=["text", "photo", "document"])
def handle_user_inputs(message):
    user_id = message.from_user.id
    current_state = user_data.get(user_id)
    print(f"[INPUT] {user_id} state={current_state}", flush=True)

    if current_state == "waiting_for_issue":
        # Пользователь отправляет обращение
        try:
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
            bot.send_message(ADMIN_ID, f"☝️ Обращение от пользователя:\nID: `{user_id}`", parse_mode="Markdown")
            user_data.pop(user_id, None)
            bot.send_message(
                message.chat.id,
                "✅ *Ваше обращение принято.*",
                reply_markup=get_main_menu(),
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"[ERR] Не удалось переслать админу: {e}", flush=True)
            bot.send_message(message.chat.id, "⚠️ Ошибка отправки. Попробуйте позже.")

    elif current_state == "ai_mode":
        if message.content_type != "text":
            bot.send_message(message.chat.id, "🤖 Нужен текстовый вопрос.")
            return
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_ai(message.text, user_id)
        bot.send_message(message.chat.id, answer, reply_markup=get_main_menu())

    else:
        # Пользователь пишет вне режима — подсказка
        bot.send_message(
            message.chat.id,
            "Выберите действие из меню ниже или нажмите «🤖 Задать вопрос ИИ».",
            reply_markup=get_main_menu(),
        )


# --- ЗАПУСК ---
if __name__ == "__main__":
    # 1. Веб-сервер для Render в фоне
    threading.Thread(target=run_health_server, daemon=True).start()
    print(f"[HTTP] Веб-сервер на порту {PORT}", flush=True)

    # 2. Проверка токена и вебхука
    try:
        me = bot.get_me()
        print(f"[INIT] Бот: @{me.username} (id={me.id})", flush=True)

        wh = bot.get_webhook_info()
        if wh.url:
            print(f"[INIT] ⚠️ Вебхук: {wh.url} — удаляю", flush=True)
            bot.remove_webhook()
        else:
            print("[INIT] Вебхук не установлен — ок", flush=True)
    except Exception as e:
        print(f"[INIT] Ошибка проверки токена: {e}", flush=True)
        raise

    # 3. Меню команд
    try:
        bot.set_my_commands([
            types.BotCommand("/start", "Запустить бота"),
            types.BotCommand("/help", "Помощь"),
        ])
    except Exception as e:
        print(f"[INIT] Ошибка меню команд: {e}", flush=True)

    # 4. Запуск polling
    print("[INIT] Запуск polling...", flush=True)
    bot.infinity_polling()
