import os
import re
import http.server
import threading
import requests
import telebot
from telebot import types

# --- НАСТРОЙКИ ---
# Вставьте сюда ваш токен от @BotFather или оставьте получение из переменных окружения
API_TOKEN = os.environ.get("TELEGRAM_TOKEN", "НОВЫЙ_ТОКЕН_ИЗ_BOTFATHER")
ADMIN_ID = 1099402750
PORT = int(os.environ.get("PORT", "10000"))

# --- НЕЙРОСЕТЬ (OpenRouter) ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_KEY", "sk-or-v1-ВАШ_КЛЮЧ_СЮДА")
AI_MODEL = "google/gemini-2.0-flash-exp:free"
AI_URL = "https://openrouter.ai"

bot = telebot.TeleBot(API_TOKEN)
user_data = {}
chat_history = {}
MAX_HISTORY = 10


# ================================================================
#   ЗАЩИТА ОТ ССЫЛОК И СПАМА
# ================================================================
# Ограничиваем регулярные выражения границами слов (\b) или точным совпадением,
# чтобы они не вырезали обычные слова из контекста (например, "информация").
URL_PATTERNS = [
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"www\.\S+", re.IGNORECASE),
    re.compile(r"t\.me/\S+", re.IGNORECASE),
    re.compile(r"telegram\.me/\S+", re.IGNORECASE),
    re.compile(r"@[A-Za-z0-9_]{3,}"),
    re.compile(r"\bподпишись\S*", re.IGNORECASE),
    re.compile(r"\bподписаться\b", re.IGNORECASE),
    re.compile(r"\bпереходи\S*", re.IGNORECASE),
    re.compile(r"\bприсоединяйся\b", re.IGNORECASE),
    re.compile(r"\bнаш канал\b", re.IGNORECASE),
    re.compile(r"\bнаш чат\b", re.IGNORECASE),
]


def strip_links(text: str) -> str:
    """Удаляет из текста только явные ссылки и рекламные призывы."""
    if not text:
        return ""
    for pattern in URL_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_send(chat_id, text, **kwargs):
    """Отправка сообщения с автоматической зачисткой ссылок."""
    text = strip_links(text)
    if not text:
        text = "(сообщение скрыто антиспам-фильтром)"
    kwargs.setdefault("disable_web_page_preview", True)
    return bot.send_message(chat_id, text, **kwargs)


def safe_edit(chat_id, message_id, text, **kwargs):
    """Редактирование сообщения с зачисткой ссылок."""
    text = strip_links(text)
    if not text:
        text = "(сообщение скрыто антиспам-фильтром)"
    kwargs.setdefault("disable_web_page_preview", True)
    return bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, **kwargs)


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
        print(f"[HTTP] Сервер запущен на порту {PORT}", flush=True)
        httpd.serve_forever()
    except Exception as e:
        print(f"[HTTP] Ошибка сервера: {e}", flush=True)


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
    markup.add(types.InlineKeyboardButton("🔙 Вернуться к темам", callback_data="info_back_to_menu"))
    return markup


# --- ДАННЫЕ СПРАВОЧНИКА ---
INFO_PAGES = {
    "docs": (
        "📋 *Документы при приёме на работу*\n\n"
        "*Основание:* ст. 26 Трудового кодекса РБ.\n\n"
        "При заключении трудового договора наниматель обязан потребовать:\n"
        "1. Паспорт или ID-карту.\n"
        "2. Трудовую книжку (при наличии).\n"
        "3. Диплом / документ об образовании.\n"
        "4. Направление на работу (для молодых специалистов).\n"
        "5. Справку о состоянии здоровья."
    ),
    "boss": (
        "🤝 *Обязанности нанимателя*\n\n"
        "Наниматель обязан предоставить работу по полученной специальности и квалификации, "
        "обеспечить условия труда, ознакомить под роспись с коллективным договором и должностной инструкцией, "
        "а также своевременно выплачивать заработную плату."
    ),
    "pension": (
        "🎓 *Распределение и стаж*\n\n"
        "Период обучения на дневном отделении в вузе или ссузе засчитывается в *общий* стаж, "
        "но не входит в *страховой* стаж (так как не платились взносы в ФСЗН).\n\n"
        "Срок работы по распределению (обычно 2 года) полноценно входит и в общий, и в страховой пенсионный стаж."
    ),
    "test": (
        "🚫 *Кому не ставится испытательный срок*\n\n"
        "*Основание:* ст. 28 Трудового кодекса РБ.\n\n"
        "Предварительное испытание *НЕ устанавливается* для:\n"
        "• молодых специалистов, направленных по распределению;\n"
        "• молодых рабочих, получивших профессионально-техническое образование;\n"
        "• граждан, принимаемых на работу по конкурсу или в порядке перевода."
    ),
    "sick": (
        "🤒 *Расчет больничного для новичков*\n\n"
        "Для молодых специалистов, у которых общий страховой стаж составляет менее 6 месяцев, "
        "пособие по временной нетрудоспособности исчисляется из размера минимальной заработной платы (МЗП) в Республике Беларусь."
    ),
    "faq": (
        "❓ *ТОП Вопросов молодых специалистов*\n\n"
        "• *Можно ли уволиться по собственному желанию?* Нет, только по соглашению сторон, в случае нарушения нанимателем условий договора или при перераспределении.\n"
        "• *Предоставляется ли жилье?* Наниматель или местный исполнительный комитет при наличии фонда могут предоставить общежитие или арендное жилье."
    ),
    "contacts": (
        "📞 *Контакты*\n\n"
        "• Отдел идеологической работы, культуры и по делам молодежи Наровлянского РИК\n"
        "• Профсоюз работников госучреждений / образования\n"
        "• При возникновении острых споров: Управление по труду, занятости и социальной защите Наровлянского райисполкома."
    ),
    "law": (
        "⚖️ *Правовая база*\n\n"
        "• Трудовой кодекс Республики Беларусь\n"
        "• Кодекс Республики Беларусь об образовании\n"
        "• Постановление Совета Министров № 1116 (о распределении и трудоустройстве)."
    )
}


# --- НЕЙРОСЕТЬ ---
SYSTEM_PROMPT = (
    "Ты — виртуальный помощник для молодых специалистов Наровлянского района (Беларусь). "
    "Помогаешь с вопросами о трудовых правах, выплатах, льготах, распределении после ВУЗа/СУЗа, "
    "жилищных условиях, больничных и т.п. Опирайся на Трудовой кодекс Республики Беларусь, "
    "Кодекс об образовании и другие нормативные акты РБ. "
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
        return "⚠️ Извините, не удалось получить ответ от нейросети. Попробуйте сформулировать вопрос позже."

    answer = strip_links(answer)
    history.append({"role": "assistant", "content": answer})

    if len(answer) > 4000:
        answer = answer[:4000] + "..."
    return answer


# --- КОМАНДЫ СТАРТ И ПОМОЩЬ ---
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    user_id = message.from_user.id
    user_data.pop(user_id, None)  # Очищаем состояние при перезапуске
    print(f"[START] Пользователь {user_id}", flush=True)

    welcome_text = (
