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
AI_URL = "https://openrouter.ai/api/v1/chat/completions"

bot = telebot.TeleBot(API_TOKEN)
user_data = {}
chat_history = {}
MAX_HISTORY = 10


# --- ЗАЩИТА ОТ ССЫЛОК (применяется ТОЛЬКО к ответам ИИ) ---
URL_PATTERNS = [
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"www\.\S+", re.IGNORECASE),
    re.compile(r"t\.me/\S+", re.IGNORECASE),
    re.compile(r"telegram\.me/\S+", re.IGNORECASE),
    re.compile(r"@[A-Za-z0-9_]{3,}"),
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
        print(f"[HTTP] Сервер на порту {PORT}", flush=True)
        httpd.serve_forever()
    except Exception as e:
        print(f"[HTTP] Ошибка: {e}", flush=True)


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

    answer = strip_links(answer)  # фильтр ТОЛЬКО к ответу ИИ
    history.append({"role": "assistant", "content": answer})

    if len(answer) > 4000:
        answer = answer[:4000] + "..."
    return answer


# --- КОМАНДА СТАРТ ---
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


# --- СПРАВОЧНИК ---
@bot.message_handler(func=lambda message: message.text == "ℹ️ Справочная информация")
def send_info_menu(message):
    print(f"[INFO] {message.from_user.id}", flush=True)
    bot.send_message(
        message.chat.id,
        "📚 *Памятка молодого специалиста*\n\nВыберите интересующую вас тему:",
        reply_markup=get_info_menu(),
        parse_mode="Markdown",
    )


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
        "*Важно:* приём оформляется приказом, трудовой договор — "
        "в письменной форме (ст. 18 ТК)."
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
        "✔️ Обеспечить условия для работы"
    ),
    "pension": (
        "🎓 *Распределение, стаж и отработка*\n\n"
        "*Основание:* Кодекс об образовании, Указ № 1 от 05.01.2024.\n\n"
        "*Сроки отработки:*\n"
        "▪️ После ВУЗа — 2 года\n"
        "▪️ После СУЗа — 1 год\n"
        "▪️ Целевое направление — по договору\n\n"
        "*Что входит в стаж:*\n"
        "✅ Очная учёба — в общий стаж\n"
        "✅ Работа по распределению — в страховой стаж\n"
        "✅ Служба в армии — в срок отработки\n"
        "✅ Отпуск по уходу за ребёнком до 3 лет"
    ),
    "test": (
        "🚫 *Кому не ставится испытательный срок*\n\n"
        "*Основание:* ст. 28 Трудового кодекса РБ.\n\n"
        "*НЕ ставится:*\n"
        "▪️ Молодым специалистам по распределению\n"
        "▪️ Молодым рабочим по направлению\n"
        "▪️ Лицам до 18 лет\n"
        "▪️ Беременным женщинам\n"
        "▪️ Женщинам с детьми до 3 лет\n"
        "▪️ При переводе к другому нанимателю\n"
        "▪️ При приёме по конкурсу\n"
        "▪️ При срочном договоре до 2 месяцев\n"
        "▪️ Инвалидам по трудовой рекомендации"
    ),
    "sick": (
        "🤒 *Больничный и выплаты*\n\n"
        "*Основание:* Закон «О пособиях по временной нетрудоспособности», "
        "Постановление Совмина № 569.\n\n"
        "*Основные правила:*\n"
        "▪️ Первые 12 дней — 80% среднедневного заработка\n"
        "▪️ С 13-го дня — 100%\n"
        "▪️ Минимум за месяц — 100% МЗП\n\n"
        "*100% с первого дня:*\n"
        "✅ Беременность и роды\n"
        "✅ Уход за ребёнком до 3 лет\n"
        "✅ Уход за больным ребёнком до 14 лет\n"
        "✅ Профзаболевание или травма на производстве"
    ),
    "faq": (
        "❓ *ТОП вопросов молодых специалистов*\n\n"
        "*1. Когда выходить на работу?*\n"
        "Как правило — с 1 августа.\n\n"
        "*2. Можно ли уволиться по собственному желанию?*\n"
        "До окончания отработки — только по уважительным причинам.\n\n"
        "*3. Входит ли декрет в отработку?*\n"
        "Да, отпуск по уходу за ребёнком до 3 лет входит.\n\n"
        "*4. Входит ли армия в отработку?*\n"
        "Да, срочная служба включается.\n\n"
        "*5. Что делать, если нет работы по специальности?*\n"
        "Обратиться в управление по труду.\n\n"
        "*6. Кто платит за переезд?*\n"
        "Наниматель компенсирует расходы и выплачивает подъёмные.\n\n"
        "*7. Какие льготы?*\n"
        "Подъёмные, компенсация переезда, льготные кредиты на жильё, общежитие."
    ),
    "contacts": (
        "📞 *Полезные контакты*\n\n"
        "*Управление по труду, занятости и соцзащите Наровлянского райисполкома*\n"
        "📍 г. Наровля, ул. Ленина, 1\n"
        "☎️ Уточните актуальный номер в райисполкоме.\n\n"
        "*Наровлянский райисполком*\n"
        "📍 г. Наровля\n\n"
        "*Профсоюзная организация* — по месту работы.\n\n"
        "*Правовая помощь:*\n"
        "▪️ Юридическая консультация района\n"
        "▪️ Бесплатная правовая помощь для отдельных категорий\n\n"
        "*Экстренные службы:* 101, 102, 103"
    ),
    "law": (
        "⚖️ *Правовая база*\n\n"
        "📘 *Трудовой кодекс Республики Беларусь*\n"
        "▪️ ст. 18 — трудовой договор\n"
        "▪️ ст. 20 — запрет требовать работу не по договору\n"
        "▪️ ст. 26 — документы при приёме\n"
        "▪️ ст. 28 — испытательный срок\n"
        "▪️ ст. 54, 55 — обязанности нанимателя\n"
        "▪️ ст. 226 — инструктаж по охране труда\n\n"
        "📗 *Кодекс об образовании РБ*\n"
        "▪️ ст. 83 — освобождение от отработки\n\n"
        "📙 *Указ Президента № 1 от 05.01.2024*\n"
        "Правила приёма на работу.\n\n"
        "📕 *Постановление Минтруда № 74 от 23.08.2011*\n"
        "О стажировке молодых специалистов.\n\n"
        "📓 *Закон «О пособиях по временной нетрудоспособности»*\n"
        "и Постановление Совмина № 569."
    ),
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


# --- ИИ-РЕЖИМ ---
@bot.message_handler(func=lambda message: message.text == "🤖 Задать вопрос ИИ")
def ai_mode(message):
    chat_history.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "🤖 Напишите ваш вопрос — я постараюсь ответить.\n\n"
        "Например: _«Какие документы нужны при приеме на работу?»_",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda message: message.text == "🧹 Очистить диалог с ИИ")
def clear_ai_history(message):
    chat_history.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "🧹 История диалога с ИИ очищена. Можете начать заново.",
        reply_markup=get_main_menu(),
    )


# --- СБОР ОБРАЩЕНИЙ ---
@bot.message_handler(func=lambda message: message.text == "⚠️ Сообщить о проблеме")
def choose_category(message):
    user_id = message.from_user.id
    user_data[user_id] = {}
    print(f"[REPORT] {user_id}", flush=True)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🏠 Жилищно-бытовые условия", callback_data="category_Жилье"),
        types.InlineKeyboardButton("💼 Трудовые споры", callback_data="category_Работа"),
        types.InlineKeyboardButton("💰 Выплаты и зарплата", callback_data="category_Деньги"),
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
        f"Вы выбрали категорию: *{category_name}*.\n\n✍️ Отправьте текст обращения. "
        "Можно прикрепить одно фото.",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_user_report)


def process_user_report(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in user_data or "category" not in user_data[user_id]:
        bot.send_message(chat_id, "⚠️ Ошибка сессии. Нажмите кнопку меню заново.", reply_markup=get_main_menu())
        return

    if message.content_type == "text" and message.text in [
        "⚠️ Сообщить о проблеме", "ℹ️ Справочная информация",
        "🤖 Задать вопрос ИИ", "🧹 Очистить диалог с ИИ",
    ]:
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
        print(f"[ADMIN] Ошибка: {e}", flush=True)
        bot.send_message(chat_id, "❌ Ошибка отправки. Попробуйте позже.", reply_markup=get_main_menu())

    user_data.pop(user_id, None)


# --- СВОБОДНЫЙ ТЕКСТ → НЕЙРОСЕТЬ ---
@bot.message_handler(
    func=lambda m: m.content_type == "text"
    and not m.text.startswith("/")
    and m.text not in [
        "⚠️ Сообщить о проблеме", "ℹ️ Справочная информация",
        "🤖 Задать вопрос ИИ", "🧹 Очистить диалог с ИИ",
    ]
)
def handle_free_question(message):
    user_id = message.from_user.id
    print(f"[FREE] {user_id}: {message.text}", flush=True)

    if user_id in user_data and "category" in user_data.get(user_id, {}):
        process_user_report(message)
        return

    bot.send_chat_action(message.chat.id, "typing")
    answer = ask_ai(message.text, user_id)
    bot.send_message(message.chat.id, answer, reply_markup=get_main_menu())


# --- ЗАПУСК ---
if __name__ == "__main__":
    threading.Thread(target=start_http_server, daemon=True).start()

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

    try:
        bot.set_my_commands([
            types.BotCommand("/start", "Запустить бота"),
            types.BotCommand("/help", "Помощь"),
        ])
    except Exception as e:
        print(f"[INIT] Ошибка меню команд: {e}", flush=True)

    print("[INIT] Запуск polling...", flush=True)
    bot.infinity_polling()
